"""Regressões de enquadramento e descarte de frames atrasados."""
import base64
import sys
import unittest
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from services.frame_stream import FrameStream
from vision.overlay import Overlay


class FrameStreamTests(unittest.TestCase):
    def test_encoder_keeps_latest_frame_while_publish_is_slow(self):
        entered, release = Event(), Event()
        received = []

        def publish(scene, image, seconds):
            received.append((scene, image, seconds))
            if len(received) == 1:
                entered.set()
                release.wait(timeout=3)

        stream = FrameStream(publish, width=160)
        image = np.full((180, 320, 3), 60, dtype=np.uint8)
        try:
            stream.submit("arrival", image, 0)
            self.assertTrue(entered.wait(timeout=2))
            for timestamp in range(1, 101):
                stream.submit("arrival", image, timestamp)
        finally:
            release.set()
            stream.close()
        self.assertFalse(stream.thread.is_alive())
        self.assertEqual([entry[2] for entry in received], [0, 100])
        jpeg = base64.b64decode(received[-1][1].split(",", 1)[1])
        decoded = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(decoded.shape[:2], (90, 160))

    def test_arrival_video_has_all_annotations_without_the_panel(self):
        frame = np.full((240, 420, 3), 60, dtype=np.uint8)
        detection = SimpleNamespace(track_id=1, bbox=(80, 60, 230, 190))
        state = SimpleNamespace(track_id=1, arrived=False, match=None, bbox=detection.bbox)
        monitor = SimpleNamespace(mode="time", states={1: state})
        region = SimpleNamespace(kind="PREFIXO", polygon=np.array([[100, 100], [170, 100], [170, 125], [100, 125]]), text="40366")
        tracker = SimpleNamespace(regions={1: [region]})
        notifier = SimpleNamespace(events=[], passengers=[])
        overlay = Overlay()
        args = (frame, [detection], monitor, tracker, notifier, 1, {"fps": 20, "detection_ms": 12}, "15/09/2026", False)
        video = overlay.render(*args, video_only=True)
        legacy = overlay.render(*args)
        self.assertEqual(video.shape, frame.shape)
        np.testing.assert_array_equal(video, legacy[76:76 + frame.shape[0], :frame.shape[1]])
        self.assertFalse(np.array_equal(video[100, 100], frame[100, 100]))
        np.testing.assert_array_equal(frame, np.full_like(frame, 60))

    def test_boarding_video_keeps_bus_person_and_prefix_boxes(self):
        frame = np.full((240, 420, 3), 60, dtype=np.uint8)
        bus = SimpleNamespace(track_id=1, bbox=(80, 60, 230, 190))
        person = SimpleNamespace(track_id=42, bbox=(260, 100, 290, 200))
        state = SimpleNamespace(number="62", track_id=1, anchor=(.5, .2), status="BUS_PARKED", emitted=set(), people_ids={42}, bus={"bus_company": "Gontijo", "bus_prefix": "14080"})
        boarding = SimpleNamespace(platforms={"62": state})
        region = SimpleNamespace(kind="PREFIXO", polygon=np.array([[100, 100], [170, 100], [170, 125], [100, 125]]), text="14080", expected_prefix="14080", exact_match=True)
        tracker = SimpleNamespace(regions={1: [region]})
        video = Overlay().render_boarding(frame, [bus], [person], boarding, tracker, None, 1, {}, False, video_only=True)
        self.assertEqual(video.shape, frame.shape)
        for y, x in [(100, 80), (150, 260), (100, 100)]:
            self.assertFalse(np.array_equal(video[y, x], frame[y, x]))


if __name__ == "__main__":
    unittest.main()
