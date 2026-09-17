"""Estados de embarque, isolamento de plataformas e notificações por viagem."""

import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from services.boarding import BoardingMonitor, load_platforms
from services.bus_matcher import load_data
from services.notification_service import NotificationService


def detection(track_id, bbox):
    return SimpleNamespace(track_id=track_id, bbox=bbox, confidence=0.9)


class BoardingTests(unittest.TestCase):
    def setUp(self):
        self.date, self.buses, self.passengers = load_data(ROOT)
        self.config = load_platforms(ROOT / "config/platforms.json", self.buses)
        self.monitor = BoardingMonitor(self.config)
        self.anchors = {"63": (0.2, 0.3), "62": (0.6, 0.3)}
        self.left = detection(1, (100, 200, 300, 700))
        self.right = detection(2, (500, 200, 700, 850))
        self.person = detection(20, (460, 680, 490, 870))

    def update(self, t, people=(), buses=None):
        return self.monitor.update([self.left, self.right] if buses is None else buses, list(people), self.anchors, t, (1000, 1000, 3))

    def test_platforms_have_correct_schedules(self):
        self.assertEqual(self.monitor.platforms["62"].bus["bus_code"], "BUS-002")
        self.assertEqual(self.monitor.platforms["63"].bus["bus_code"], "BUS-003")

    def test_prefix_confirmation_is_latched_per_occupancy(self):
        state = self.monitor.platforms["62"]
        self.assertFalse(state.validate_prefix([SimpleNamespace(text="1080", confidence=0.9)]))
        self.assertTrue(state.validate_prefix([SimpleNamespace(text="14080", confidence=0.9)]))
        state.track_id = 77
        state.lost = True
        self.assertTrue(state.validate_prefix([]))
        self.assertTrue(state.validate_prefix([SimpleNamespace(text="1080", confidence=0.9)]))
        self.assertFalse(self.monitor.platforms["63"].validate_prefix([]))
        state.bus = dict(state.bus, bus_prefix="99999")
        self.assertFalse(state.validate_prefix([]))

    def test_departure_clears_prefix_confirmation(self):
        state = self.monitor.platforms["62"]
        reading = SimpleNamespace(text="14080", confidence=0.9)
        self.assertTrue(state.validate_prefix([reading]))
        self.monitor._emit(state, "BUS_DEPARTED", 30, "TEST")
        self.assertIsNone(state.confirmed_prefix)
        self.assertFalse(state.validate_prefix([reading]))

    def test_new_scene_does_not_inherit_prefix_confirmation(self):
        state = self.monitor.platforms["62"]
        state.validate_prefix([SimpleNamespace(text="14080", confidence=0.9)])
        fresh = BoardingMonitor(self.config)
        self.assertFalse(fresh.platforms["62"].validate_prefix([]))

    def test_presence_and_parking_notify_once_for_each_bus(self):
        events = [e for step in range(40) for e in self.update(step / 4)]
        self.assertEqual(sum(e["event"] == "BUS_AT_PLATFORM" for e in events), 2)
        self.assertEqual(sum(e["event"] == "BUS_PARKED" for e in events), 2)
        self.assertFalse(any(e["event"].startswith("BOARDING") for e in events))

    def test_start_reports_count_and_finish_waits_for_quiet_window(self):
        events = [e for step in range(40) for e in self.update(step / 4, [self.person])]
        start = [e for e in events if e["event"] == "BOARDING_STARTED"]
        self.assertEqual(len(start), 1)
        self.assertEqual(start[0]["platform"], "62")
        self.assertEqual(start[0]["people_count"], 1)
        short_gap = [e for step in range(40, 72) for e in self.update(step / 4)]
        self.assertFalse(any(e["event"] == "BOARDING_FINISHED" for e in short_gap))
        finished = [e for step in range(72, 112) for e in self.update(step / 4)]
        self.assertEqual(sum(e["event"] == "BOARDING_FINISHED" for e in finished), 1)
        self.assertFalse(any(e["event"] == "BUS_DEPARTED" for e in finished))

    def test_single_person_frame_does_not_start_boarding(self):
        for step in range(24):
            self.update(step / 4)
        events = self.update(6, [self.person])
        events.extend(e for step in range(25, 40) for e in self.update(step / 4))
        self.assertFalse(any(e["event"] == "BOARDING_STARTED" for e in events))

    def test_driver_inside_bus_is_not_counted_as_waiting_person(self):
        driver = detection(30, (570, 300, 610, 500))
        self.update(0, [self.person, driver])
        self.assertEqual(self.monitor.platforms["62"].people_count, 1)
        self.assertEqual(self.monitor.platforms["63"].people_count, 0)

    def test_camera_translation_does_not_create_departure(self):
        for step in range(32):
            self.update(step / 4)
        self.anchors = {"63": (0.3, 0.4), "62": (0.7, 0.4)}
        self.left = detection(1, (200, 300, 400, 800))
        self.right = detection(2, (600, 300, 800, 950))
        events = [e for step in range(32, 60) for e in self.update(step / 4)]
        self.assertFalse(any(e["event"] == "BUS_DEPARTED" for e in events))

    def test_missing_detections_are_not_departure_or_boarding_finish(self):
        for step in range(40):
            self.update(step / 4, [self.person])
        events = [e for step in range(40, 120) for e in self.update(step / 4, buses=[])]
        self.assertEqual(events, [])

    def test_moving_out_departure_is_not_repeated(self):
        for step in range(40):
            self.update(step / 4, [self.person])
        self.right = detection(2, (500, 180, 650, 480))
        events = [e for step in range(40, 80) for e in self.update(step / 4)]
        self.assertEqual(sum(e["event"] == "BUS_DEPARTED" for e in events), 1)
        self.assertEqual(sum(e["event"] == "BOARDING_FINISHED" for e in events), 1)
        self.assertEqual(events[-1]["bus"]["bus_code"], "BUS-002")

    def test_detection_gap_restarts_departure_confirmation(self):
        for step in range(40):
            self.update(step / 4)
        self.right = detection(2, (500, 180, 650, 480))
        self.update(10)
        self.update(11, buses=[])
        resumed = self.update(20)
        self.assertFalse(any(e["event"] == "BUS_DEPARTED" for e in resumed))
        confirmed = [e for step in range(81, 94) for e in self.update(step / 4)]
        self.assertEqual(sum(e["event"] == "BUS_DEPARTED" for e in confirmed), 1)

    def test_tracker_id_change_does_not_repeat_platform_arrival(self):
        events = [e for step in range(24) for e in self.update(step / 4)]
        self.right = detection(77, self.right.bbox)
        events.extend(e for step in range(24, 48) for e in self.update(step / 4))
        self.assertEqual(sum(e["event"] == "BUS_AT_PLATFORM" and e["platform"] == "62" for e in events), 1)

    def test_notifier_targets_only_passengers_of_the_platform_bus(self):
        notifier = NotificationService(self.passengers)
        observation = {"event": "BOARDING_STARTED", "platform": "62", "bus": self.buses[1], "video_seconds": 25, "track_id": 2, "people_count": 3, "evidence": "TEST"}
        with redirect_stdout(StringIO()) as console:
            event = notifier.notify_boarding(observation, self.date, 30)
            duplicate = notifier.notify_boarding(observation, self.date, 30)
        self.assertEqual(event["passenger_codes"], ["PASS-004", "PASS-005"])
        self.assertEqual(event["sequence_seconds"], 55)
        self.assertIn("3 pessoas", event["message"])
        self.assertEqual(console.getvalue().count("[NOTIFICACAO]"), 2)
        self.assertIsNone(duplicate)


if __name__ == "__main__":
    unittest.main()
