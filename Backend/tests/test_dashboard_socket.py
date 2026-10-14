"""Integração do transporte real, sem carregar os modelos de visão."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from websockets.sync.client import connect
from services.dashboard_socket import DashboardSocket
from services.notification_service import NotificationService


class DashboardSocketTests(unittest.TestCase):
    def setUp(self):
        schedules = json.loads((ROOT / "bus_schedules.json").read_text(encoding="utf-8-sig"))
        self.date = next(iter(schedules))
        self.buses = schedules[self.date]
        self.passengers = json.loads((ROOT / "passengers.json").read_text(encoding="utf-8-sig"))["passengers"]
        self.server = DashboardSocket(self.date, self.buses, self.passengers, port=0)
        self.server.start()
        self.url = f"ws://127.0.0.1:{self.server.port}"
        self.notifier = NotificationService(self.passengers, self.server.publish)

    def tearDown(self):
        self.server.close()
        self.assertFalse(self.server.thread.is_alive())

    def read(self, client):
        return json.loads(client.recv(timeout=3))

    def test_snapshot_broadcast_and_reconnect_history(self):
        with connect(self.url) as first, connect(self.url) as second:
            for client in [first, second]:
                snapshot = self.read(client)
                self.assertEqual(snapshot["type"], "snapshot")
                self.assertEqual(len(snapshot["payload"]["passengers"]), len(self.passengers))
                self.assertEqual(snapshot["payload"]["events"], [])
            event = self.notifier.notify(self.buses[0], self.date, 21, 1, "time", .99)
            received = self.read(first)
            self.assertEqual(received["type"], "event")
            self.assertEqual(received["payload"]["passenger_codes"], event["passenger_codes"])
            self.assertEqual(received, self.read(second))
        with connect(self.url) as reconnect:
            snapshot = self.read(reconnect)["payload"]
            self.assertEqual(len(snapshot["events"]), 1)
            self.assertEqual(snapshot["events"][0]["id"], received["payload"]["id"])
            self.server.set_status("completed")
            self.assertEqual(self.read(reconnect), {"type": "status", "payload": "completed"})

    def test_frame_replay_and_boarding_deduplication(self):
        with connect(self.url) as client:
            self.read(client)
            image = "data:image/jpeg;base64,dGVzdA=="
            self.server.publish_frame("boarding", image, 12.345)
            frame = self.read(client)
            self.assertEqual(frame["payload"]["seconds"], 12.35)
            observation = {"bus": self.buses[1], "platform": "62", "event": "BOARDING_STARTED", "people_count": 4, "video_seconds": 15}
            self.notifier.notify_boarding(observation, self.date)
            event = self.read(client)["payload"]
            self.assertEqual(len(event["passenger_codes"]), 2)
            self.assertIsNone(self.notifier.notify_boarding(observation, self.date))
            with connect(self.url) as late:
                state = self.read(late)["payload"]
                self.assertEqual(state["frames"]["boarding"]["image"], image)
                self.assertEqual(len(state["events"]), 1)


if __name__ == "__main__":
    unittest.main()
