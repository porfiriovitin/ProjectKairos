"""Fluxo óptico validado em imagem sintética, sem baixar modelos."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vision.text_tracker import TextRegion, TextTracker, follow_groups


class TextTrackerTests(unittest.TestCase):
    def setUp(self):
        random = np.random.default_rng(42)
        self.image = random.integers(0, 255, (180, 240), dtype=np.uint8)
        self.image = cv2.GaussianBlur(self.image, (3, 3), 0)
        mask = np.zeros_like(self.image)
        mask[50:100, 50:150] = 255
        self.points = cv2.goodFeaturesToTrack(self.image, 20, 0.05, 5, mask=mask)
        self.polygon = np.float32([[50, 50], [150, 50], [150, 100], [50, 100]])

    def test_boxes_follow_measured_translation(self):
        current = cv2.warpAffine(self.image, np.float32([[1, 0, 5], [0, 1, 3]]), (240, 180))
        motions = follow_groups(self.image, current, [self.points[:10], self.points[10:]])
        for matrix, _ in motions:
            np.testing.assert_allclose(matrix[:, 2], [5, 3], atol=0.6)

    def test_expired_and_missing_tracks_remove_boxes(self):
        tracker = TextTracker()
        tracker.previous_gray = self.image
        tracker.regions[1] = [TextRegion("EMPRESA", "EMPRESA", self.polygon, self.points, 0)]
        tracker.update(self.image, {1}, 5)
        self.assertEqual(tracker.regions[1], [])
        tracker.update(self.image, set(), 5.1)
        self.assertNotIn(1, tracker.regions)

    def test_missing_new_reading_does_not_erase_valid_tracked_box(self):
        tracker = TextTracker()
        tracker.regions[1] = [TextRegion("EMPRESA", "EMPRESA", self.polygon, self.points, 1)]
        result = SimpleNamespace(track_id=1, timestamp=1.5, gray=self.image, readings=[])
        tracker.accept(result, self.image, 1.5, None)
        self.assertEqual(len(tracker.regions[1]), 1)


if __name__ == "__main__":
    unittest.main()
