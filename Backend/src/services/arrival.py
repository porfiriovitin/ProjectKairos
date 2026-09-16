"""Estado por track e confirmação de chegada sem duplicação por execução."""

from collections import deque
from dataclasses import dataclass, field

from services.bus_matcher import Match


@dataclass
class VehicleState:
    track_id: int
    bbox: tuple
    first_seen: float
    last_seen: float
    detections: int = 0
    zone_hits: int = 0
    last_ocr: float = -100.0
    history: deque = field(default_factory=lambda: deque(maxlen=12))
    match: Match | None = None
    arrived: bool = False


class ArrivalMonitor:
    def __init__(self, mode: str, arrival_seconds: float, zone: list[float]):
        self.mode = mode
        self.arrival_seconds = arrival_seconds
        self.zone = zone
        self.states: dict[int, VehicleState] = {}
        self.processed_buses: set[tuple[str, str]] = set()

    def observe(self, detections: list, timestamp: float, shape: tuple) -> None:
        height, width = shape[:2]
        active = {d.track_id for d in detections}
        for track_id in list(self.states):
            state = self.states[track_id]
            if track_id not in active:
                state.zone_hits = 0
            if timestamp - state.last_seen > 3.0:
                del self.states[track_id]
        for detection in detections:
            state = self.states.get(detection.track_id)
            if state is None:
                state = VehicleState(detection.track_id, detection.bbox, timestamp, timestamp)
                self.states[detection.track_id] = state
            state.bbox = detection.bbox
            state.last_seen = timestamp
            state.detections += 1
            x1, _, x2, y2 = detection.bbox
            point = ((x1 + x2) / (2 * width), y2 / height)
            zx1, zy1, zx2, zy2 = self.zone
            inside = zx1 <= point[0] <= zx2 and zy1 <= point[1] <= zy2
            state.zone_hits = state.zone_hits + 1 if inside else 0

    def arrivals(self, timestamp: float, date: str):
        for state in self.states.values():
            if state.last_seen != timestamp or state.detections < 3:
                continue
            if not state.match or not state.match.confirmed:
                continue
            key = (date, state.match.bus["bus_code"])
            if key in self.processed_buses:
                state.arrived = True
                continue
            ready = timestamp >= self.arrival_seconds if self.mode == "time" else state.zone_hits >= 3
            if ready:
                self.processed_buses.add(key)
                state.arrived = True
                yield state
