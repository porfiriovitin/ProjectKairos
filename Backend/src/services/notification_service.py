"""Único ponto de saída dos eventos e notificações do MVP."""

import json


class NotificationService:
    def __init__(self, passengers: list[dict], event_sink=None):
        self.passengers = passengers
        self.event_sink = event_sink
        self.events: list[dict] = []
        self.sent_boarding_events = set()

    def notify_boarding(self, observation: dict, date: str, timeline_offset: float = 0.0):
        bus = observation["bus"]
        key = (date, bus["bus_code"], observation["platform"], observation["event"])
        if key in self.sent_boarding_events:
            return None
        self.sent_boarding_events.add(key)
        passengers = [p for p in self.passengers if p["bus_code"] == bus["bus_code"]]
        platform = observation["platform"]
        count = observation["people_count"]
        messages = {
            "BUS_AT_PLATFORM": f"Seu ônibus está na plataforma {platform}.",
            "BUS_PARKED": f"Seu ônibus está parado na plataforma {platform}.",
            "BOARDING_STARTED": f"Embarque iniciado na plataforma {platform}. Há {count} pessoas visíveis na área de embarque.",
            "BOARDING_FINISHED": f"Embarque encerrado na plataforma {platform}.",
            "BUS_DEPARTED": f"Seu ônibus saiu da plataforma {platform}.",
        }
        event = {
            **{key: value for key, value in observation.items() if key != "bus"},
            "bus_code": bus["bus_code"], "bus_company": bus["bus_company"],
            "bus_prefix": bus["bus_prefix"], "itinerary": bus["itinerary"],
            "schedule_date": date, "scene": "boarding",
            "video_seconds": round(observation["video_seconds"], 2),
            "sequence_seconds": round(timeline_offset + observation["video_seconds"], 2),
            "identity_source": "CONFIGURED_PLATFORM_SCHEDULE_ASSOCIATION",
            "people_count_source": "YOLO_VISIBLE_PEOPLE_IN_ACCESS_ZONE",
            "passenger_codes": [p["passenger_code"] for p in passengers],
            "message": messages[observation["event"]],
        }
        self.events.append(event)
        if self.event_sink:
            self.event_sink(event)
        print("\n" + "=" * 68)
        print("[EVENT] " + json.dumps(event, ensure_ascii=False))
        for passenger in passengers:
            print(f"[NOTIFICACAO] {passenger['name']} ({passenger['passenger_code']})")
            print(event["message"])
        print("=" * 68, flush=True)
        return event

    def notify(self, bus: dict, date: str, timestamp: float, track_id: int, mode: str, score: float):
        passengers = [p for p in self.passengers if p["bus_code"] == bus["bus_code"]]
        event = {
            "event": "BUS_ARRIVED",
            "bus_code": bus["bus_code"],
            "bus_company": bus["bus_company"],
            "bus_prefix": bus["bus_prefix"],
            "itinerary": bus["itinerary"],
            "schedule_date": date,
            "video_seconds": round(timestamp, 2),
            "track_id": track_id,
            "arrival_rule": "SIMULATED_VIDEO_TIME" if mode == "time" else "ZONE_PRESENCE",
            "identity_source": "YOLO_EASYOCR_SCHEDULE_MATCH",
            "match_score": round(score, 3),
            "passenger_codes": [p["passenger_code"] for p in passengers],
            "message": "Seu ônibus chegou à rodoviária. Acompanhe as próximas informações de embarque.",
        }
        self.events.append(event)
        if self.event_sink:
            self.event_sink(event)
        print("\n" + "=" * 68)
        print("[EVENT] " + json.dumps(event, ensure_ascii=False))
        for passenger in passengers:
            print(f"[NOTIFICACAO] {passenger['name']} ({passenger['passenger_code']})")
            print("Seu ônibus chegou à rodoviária. Acompanhe as próximas informações de embarque.")
        print("=" * 68, flush=True)
        return event
