"""Testes das regras que impedem falsos positivos e notificações duplicadas."""

import sys
import unittest
from collections import deque
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from services.arrival import ArrivalMonitor
from services.bus_matcher import BusMatcher, load_data, normalize
from services.notification_service import NotificationService


def readings(*texts):
    return [SimpleNamespace(text=text, confidence=0.9) for text in texts]


def history(*samples):
    return deque((float(i), readings(*sample)) for i, sample in enumerate(samples))


class MatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.date, cls.buses, cls.passengers = load_data(ROOT)

    def setUp(self):
        self.matcher = BusMatcher(self.buses)

    def test_single_frame_does_not_confirm(self):
        match = self.matcher.match(history(("ITAPEMIRIM", "40366")))
        self.assertEqual(match.bus["bus_code"], "BUS-001")
        self.assertFalse(match.confirmed)

    def test_no_prefix_means_no_confirmation(self):
        match = self.matcher.match(history(*[("ITAPEMIRIM", "SAIDA 14:30")] * 4))
        self.assertFalse(match.confirmed)

    def test_ocr_typo_is_resolved_using_schedule(self):
        match = self.matcher.match(history(*[("ITAPEM1RIM", "4036G")] * 3))
        self.assertEqual(match.bus["bus_code"], "BUS-001")
        self.assertTrue(match.confirmed)

    def test_evidence_can_come_from_different_frames(self):
        match = self.matcher.match(history(("ITAPEMIRIM",), ("40366",), ("ITAPEMIRIM", "40366")))
        self.assertTrue(match.confirmed)

    def test_other_bus_is_not_forced_to_demo_bus(self):
        match = self.matcher.match(history(*[("COMETA", "17304")] * 3))
        self.assertEqual(match.bus["bus_code"], "BUS-006")
        self.assertTrue(match.confirmed)

    def test_background_text_cannot_replace_missing_company(self):
        match = self.matcher.match(history(*[("COMETA", "40366")] * 3))
        self.assertFalse(match.confirmed)

    def test_ambiguous_trip_is_not_chosen_arbitrarily(self):
        duplicate = {**self.buses[0], "bus_code": "ANOTHER-TRIP"}
        matcher = BusMatcher([self.buses[0], duplicate])
        self.assertFalse(matcher.match(history(*[("ITAPEMIRIM", "40366")] * 3)).confirmed)

    def test_empty_ocr_has_no_match(self):
        self.assertIsNone(self.matcher.match(history((), (), ())))

    def test_led_time_spacing_and_comma_are_normalized(self):
        self.assertEqual(normalize("Saída 14, 30"), "SAIDA 14:30")
        self.assertEqual(self.matcher.classify_text("SAIDA 14: 30"), "HORARIO")

    def test_low_confidence_text_cannot_confirm_identity(self):
        samples = history(*[("ITAPEMIRIM", "40366")] * 3)
        for _, sample in samples:
            for reading in sample:
                reading.confidence = 0.10
        self.assertIsNone(self.matcher.match(samples))

    def test_passengers_include_those_without_check_in(self):
        service = NotificationService(self.passengers)
        with redirect_stdout(StringIO()) as output:
            event = service.notify(self.buses[0], self.date, 20, 1, "time", 0.9)
        self.assertEqual(event["passenger_codes"], ["PASS-001", "PASS-002", "PASS-003"])
        self.assertEqual(output.getvalue().count("[NOTIFICACAO]"), 3)


class ArrivalTests(unittest.TestCase):
    def setUp(self):
        self.date, buses, _ = load_data(ROOT)
        self.match = BusMatcher(buses).match(history(*[("ITAPEMIRIM", "40366")] * 3))
        self.monitor = ArrivalMonitor("time", 20.0, [0.35, 0.65, 0.95, 0.98])
        self.detection = SimpleNamespace(track_id=1, bbox=(40, 10, 80, 90))

    def observe(self, timestamp, track_id=1):
        self.detection.track_id = track_id
        self.monitor.observe([self.detection], timestamp, (100, 100, 3))
        self.monitor.states[track_id].match = self.match
        return list(self.monitor.arrivals(timestamp, self.date))

    def test_time_gate_requires_repeated_detection_and_identification(self):
        self.assertEqual(self.observe(18), [])
        self.assertEqual(self.observe(19), [])
        self.assertEqual(len(self.observe(20)), 1)
        self.assertEqual(self.observe(21), [])

    def test_reacquired_track_cannot_notify_same_bus_twice(self):
        for t in (18, 19, 20):
            self.observe(t)
        self.assertEqual(self.observe(21, 2), [])
        self.assertEqual(self.observe(22, 2), [])
        self.assertEqual(self.observe(23, 2), [])
        self.assertTrue(self.monitor.states[2].arrived)

    def test_zone_requires_three_consecutive_detections(self):
        self.monitor.mode = "zone"
        self.assertEqual(self.observe(1), [])
        self.assertEqual(self.observe(2), [])
        self.monitor.observe([], 2.5, (100, 100, 3))
        self.assertEqual(self.observe(3), [])
        self.assertEqual(self.observe(4), [])
        self.assertEqual(len(self.observe(5)), 1)

    def test_inactive_track_cannot_emit_arrival(self):
        self.observe(17)
        self.observe(18)
        self.observe(19)
        self.monitor.observe([], 20, (100, 100, 3))
        self.assertEqual(list(self.monitor.arrivals(20, self.date)), [])

    def test_unidentified_vehicle_never_emits(self):
        for t in (20, 21, 22):
            self.monitor.observe([self.detection], t, (100, 100, 3))
        self.assertEqual(list(self.monitor.arrivals(22, self.date)), [])


if __name__ == "__main__":
    unittest.main()
