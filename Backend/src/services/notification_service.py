"""Único ponto de saída dos eventos e notificações do MVP."""

import json


class NotificationService:
    def __init__(self, passengers: list[dict]):
        self.passengers = passengers
        self.events: list[dict] = []

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
        }
        self.events.append(event)
        print("\n" + "=" * 68)
        print("[EVENT] " + json.dumps(event, ensure_ascii=False))
        for passenger in passengers:
            print(f"[NOTIFICACAO] {passenger['name']} ({passenger['passenger_code']})")
            print("Seu ônibus chegou à rodoviária. Acompanhe as próximas informações de embarque.")
        print("=" * 68, flush=True)
        return event
