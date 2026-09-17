"""Localização geométrica sem consultar o número esperado."""

import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vision.prefix_region import locate_prefix


class PrefixRegionTests(unittest.TestCase):
    def test_finds_digits_on_yellow_panel(self):
        frame = np.full((400, 500, 3), 180, np.uint8)
        cv2.rectangle(frame, (120, 290), (380, 345), (0, 220, 240), -1)
        cv2.putText(frame, "14080", (180, 325), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
        bounds = locate_prefix(frame, (80, 50, 420, 380))
        self.assertIsNotNone(bounds)
        left, top, right, bottom = bounds
        self.assertTrue(170 <= left <= 190)
        self.assertTrue(290 <= top < bottom <= 340)
        self.assertTrue(250 < right < 290)

    def test_no_yellow_panel_does_not_invent_a_region(self):
        frame = np.full((400, 500, 3), 180, np.uint8)
        self.assertIsNone(locate_prefix(frame, (80, 50, 420, 380)))

    def test_empty_crop_does_not_crash(self):
        frame = np.zeros((40, 50, 3), np.uint8)
        self.assertIsNone(locate_prefix(frame, (0, 0, 0, 0)))
