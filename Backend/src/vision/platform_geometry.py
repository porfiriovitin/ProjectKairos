"""Acompanha as placas de referência para compensar movimentos da câmera."""

import cv2
import numpy as np


class PlatformGeometry:
    def __init__(self, platforms):
        self.platforms = platforms
        self.anchors = {p["number"]: tuple(p["anchor"]) for p in platforms}
        self.last_detection = -100.0
        self.templates = {}
        self.confidence = {}

    def update(self, frame, timestamp):
        if timestamp - self.last_detection < 0.2:
            return self.anchors
        self.last_detection = timestamp
        height, width = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if not self.templates:
            for platform in self.platforms:
                x1, y1, x2, y2 = platform["sign_box"]
                self.templates[platform["number"]] = gray[int(y1 * height):int(y2 * height), int(x1 * width):int(x2 * width)].copy()
        for number in ("62", "63"):
            x, y = self.anchors[number]
            if number == "63":
                right_x, right_y = self.anchors["62"]
                x, y = right_x - 0.29, right_y
                margin_x, margin_y = 0.13, 0.10
            else:
                margin_x, margin_y = 0.17, 0.15
            left, top = max(0, int((x - margin_x) * width)), max(0, int((y - margin_y) * height))
            right, bottom = min(width, int((x + margin_x) * width)), min(height, int((y + margin_y) * height))
            search = gray[top:bottom, left:right]
            best = (-1, None)
            for scale in (0.80, 0.90, 1.0, 1.10):
                template = cv2.resize(self.templates[number], None, fx=scale, fy=scale)
                th, tw = template.shape
                if search.shape[0] < th or search.shape[1] < tw:
                    continue
                scores = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
                _, score, _, position = cv2.minMaxLoc(scores)
                point = ((left + position[0] + tw / 2) / width, (top + position[1] + th / 2) / height)
                if score > best[0]:
                    best = score, point
            self.confidence[number] = best[0]
            if best[0] >= 0.45:
                self.anchors[number] = best[1]
        return self.anchors


def platform_zone(anchor, width, height):
    """Zona de ocupação aproximada, relativa à placa da plataforma."""
    x, y = anchor
    return np.array([
        [(x - 0.14) * width, (y + 0.25) * height],
        [(x + 0.14) * width, (y + 0.25) * height],
        [(x + 0.17) * width, min(0.99, y + 0.56) * height],
        [(x - 0.18) * width, min(0.99, y + 0.56) * height],
    ], dtype=np.int32)
