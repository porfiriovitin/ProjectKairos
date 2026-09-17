"""Estados das plataformas, contagem visual e eventos com confirmação temporal."""

import json
import math
from collections import deque
from dataclasses import dataclass, field


EVENT_TITLES = {
    "BUS_AT_PLATFORM": "ONIBUS NA PLATAFORMA",
    "BUS_PARKED": "ONIBUS PARADO",
    "BOARDING_STARTED": "EMBARQUE INICIADO",
    "BOARDING_FINISHED": "EMBARQUE ENCERRADO",
    "BUS_DEPARTED": "ONIBUS SAIU",
}


def load_platforms(path, buses):
    with path.open(encoding="utf-8") as file:
        config = json.load(file)
    by_code = {bus["bus_code"]: bus for bus in buses}
    seen = set()
    for platform in config["platforms"]:
        if platform["number"] in seen:
            raise ValueError("Número de plataforma repetido na configuração.")
        seen.add(platform["number"])
        bus = by_code[platform["bus_code"]]
        if str(bus.get("boarding_platform")) != platform["number"]:
            raise ValueError(f"Plataforma de {bus['bus_code']} diverge da programação.")
        platform["bus"] = bus
    return config


@dataclass
class PlatformState:
    number: str
    bus: dict
    anchor: tuple
    track_id: int | None = None
    bbox: tuple | None = None
    last_seen: float = -100.0
    first_seen: float | None = None
    status: str = "AGUARDANDO ONIBUS"
    emitted: set = field(default_factory=set)
    positions: deque = field(default_factory=lambda: deque(maxlen=180))
    presence_since: float | None = None
    stopped_since: float | None = None
    boarding_since: float | None = None
    quiet_since: float | None = None
    departing_since: float | None = None
    people_count: int = 0
    people_ids: set = field(default_factory=set)
    door_ids: set = field(default_factory=set)
    last_door_presence: float = -100.0
    peak_count: int = 0
    boarding_started_at: float | None = None
    lost: bool = False
    confirmed_prefix: str | None = None

    def validate_prefix(self, readings):
        """Confirma uma vez por ocupação, independentemente de perdas breves do track."""
        expected = str(self.bus["bus_prefix"])
        if "BUS_DEPARTED" in self.emitted:
            self.confirmed_prefix = None
            return False
        if self.confirmed_prefix != expected:
            self.confirmed_prefix = None
            if any(r.confidence >= 0.5 and r.text.strip() == expected for r in readings):
                self.confirmed_prefix = expected
        return self.confirmed_prefix == expected


class BoardingMonitor:
    def __init__(self, config):
        self.config = config
        self.platforms = {p["number"]: PlatformState(p["number"], p["bus"], tuple(p["anchor"])) for p in config["platforms"]}

    def _emit(self, state, kind, timestamp, evidence):
        if kind in state.emitted:
            return None
        state.emitted.add(kind)
        if kind == "BUS_DEPARTED":
            state.confirmed_prefix = None
        state.status = EVENT_TITLES[kind]
        return {
            "event": kind, "platform": state.number, "bus": state.bus,
            "track_id": state.track_id, "video_seconds": timestamp,
            "people_count": state.people_count, "peak_people_count": state.peak_count,
            "evidence": evidence,
        }

    def update(self, buses, people, anchors, timestamp, shape):
        height, width = shape[:2]
        events = []
        assigned = set()
        detections = {d.track_id: d for d in buses}
        # IDs existentes têm preferência. Outro ônibus não assume a plataforma durante uma manobra.
        selected = {}
        for number, state in self.platforms.items():
            state.anchor = anchors[number]
            if "BUS_DEPARTED" not in state.emitted and state.track_id in detections:
                selected[number] = detections[state.track_id]
                assigned.add(state.track_id)
        for number, state in self.platforms.items():
            if number in selected or "BUS_DEPARTED" in state.emitted:
                continue
            ax, ay = state.anchor
            eligible = []
            for detection in buses:
                if detection.track_id in assigned:
                    continue
                x1, y1, x2, y2 = detection.bbox
                center = (x1 + x2) / (2 * width)
                if abs(center - ax) <= 0.14 and y2 / height - ay >= 0.25 and (y2 - y1) / height >= 0.22:
                    eligible.append((abs(center - ax), detection))
            if eligible:
                detection = min(eligible, key=lambda item: item[0])[1]
                selected[number] = detection
                assigned.add(detection.track_id)

        # Cada pessoa pertence no máximo a uma plataforma. Motoristas dentro do para-brisa são excluídos.
        counts = {number: set() for number in self.platforms}
        doors = {number: set() for number in self.platforms}
        for person in people:
            px1, py1, px2, py2 = person.bbox
            foot = ((px1 + px2) / 2, py2)
            choices = []
            for number, detection in selected.items():
                state = self.platforms[number]
                if "BUS_DEPARTED" in state.emitted:
                    continue
                x1, y1, x2, y2 = detection.bbox
                bw, bh = x2 - x1, y2 - y1
                # Lado de acesso visto pela câmera, incluindo a aproximação à porta.
                if x1 - 0.55 * bw <= foot[0] <= x1 + 0.18 * bw and y1 + 0.63 * bh <= foot[1] <= y2 + 0.22 * bh:
                    distance = abs(foot[0] - x1) / bw + abs(foot[1] - (y1 + 0.90 * bh)) / bh
                    choices.append((distance, number))
            if choices:
                _, number = min(choices)
                counts[number].add(person.track_id)
                x1, y1, x2, y2 = selected[number].bbox
                if foot[0] >= x1 - 0.40 * (x2 - x1) and foot[1] <= y2 + 0.22 * (y2 - y1):
                    doors[number].add(person.track_id)

        for number, state in self.platforms.items():
            if "BUS_DEPARTED" in state.emitted:
                continue
            state.people_ids = counts[number]
            state.door_ids = doors[number]
            state.people_count = len(counts[number])
            if state.door_ids:
                state.last_door_presence = timestamp
            state.peak_count = max(state.peak_count, state.people_count)
            detection = selected.get(number)
            if detection is None:
                state.lost = timestamp - state.last_seen > 0.8
                state.presence_since = None
                state.stopped_since = None
                state.boarding_since = None
                state.departing_since = None
                state.last_door_presence = -100.0
                # Falha isolada de YOLO/oclusão não prova saída nem fim de embarque.
                state.quiet_since = None
                continue
            state.lost = False
            state.track_id = detection.track_id
            state.bbox = detection.bbox
            state.last_seen = timestamp
            if state.first_seen is None:
                state.first_seen = timestamp
            x1, y1, x2, y2 = detection.bbox
            ax, ay = state.anchor
            position = ((x1 + x2) / (2 * width) - ax, y2 / height - ay)
            state.positions.append((timestamp, position))
            while state.positions and timestamp - state.positions[0][0] > 2.0:
                state.positions.popleft()
            docked = abs(position[0]) <= 0.145 and position[1] >= 0.285
            if docked:
                state.departing_since = None
                if state.presence_since is None:
                    state.presence_since = timestamp
                if timestamp - state.presence_since >= self.config["presence_seconds"]:
                    event = self._emit(state, "BUS_AT_PLATFORM", timestamp, "PERSISTENT_BUS_IN_PLATFORM_ZONE")
                    if event:
                        events.append(event)
                old_time, old_position = state.positions[0]
                stable = timestamp - old_time >= 1.0 and math.dist(position, old_position) < 0.022
                if stable:
                    if state.stopped_since is None:
                        state.stopped_since = timestamp
                else:
                    state.stopped_since = None
                if "BUS_AT_PLATFORM" in state.emitted and state.stopped_since is not None and timestamp - state.stopped_since >= self.config["stationary_seconds"]:
                    event = self._emit(state, "BUS_PARKED", timestamp, "STABLE_BUS_POSITION_RELATIVE_TO_PLATFORM_SIGN")
                    if event:
                        events.append(event)
                if "BUS_PARKED" in state.emitted:
                    if timestamp - state.last_door_presence <= 0.75:
                        state.quiet_since = None
                        if state.boarding_since is None:
                            state.boarding_since = timestamp
                        if state.door_ids and timestamp - state.boarding_since >= self.config["boarding_presence_seconds"]:
                            event = self._emit(state, "BOARDING_STARTED", timestamp, "SUSTAINED_PERSON_PRESENCE_AT_BOARDING_ACCESS")
                            if event:
                                state.boarding_started_at = timestamp
                                events.append(event)
                    else:
                        state.boarding_since = None
                        if state.quiet_since is None:
                            state.quiet_since = timestamp
                        if state.boarding_started_at is not None and timestamp - state.quiet_since >= self.config["boarding_quiet_seconds"]:
                            event = self._emit(state, "BOARDING_FINISHED", timestamp, "BOARDING_ACCESS_WITHOUT_PEOPLE_FOR_QUIET_WINDOW")
                            if event:
                                events.append(event)
            else:
                state.presence_since = None
                state.stopped_since = None
                state.boarding_since = None
                state.quiet_since = None
                if "BUS_AT_PLATFORM" in state.emitted:
                    if state.departing_since is None:
                        state.departing_since = timestamp
                    if timestamp - state.departing_since >= self.config["departure_seconds"]:
                        if "BOARDING_STARTED" in state.emitted:
                            event = self._emit(state, "BOARDING_FINISHED", timestamp, "BUS_LEAVING_PLATFORM")
                            if event:
                                events.append(event)
                        event = self._emit(state, "BUS_DEPARTED", timestamp, "TRACKED_BUS_MOVED_OUT_OF_PLATFORM_ZONE")
                        if event:
                            events.append(event)
        return events
