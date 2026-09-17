"""YOLO detecta ônibus; ByteTrack mantém IDs ao longo do vídeo."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from ultralytics import YOLO


@dataclass
class Detection:
    track_id: int
    bbox: tuple[int, int, int, int]
    confidence: float
    kind: str = "bus"


class BusDetector:
    def __init__(self, model_path: Path, device: str, image_size: int):
        model_path.parent.mkdir(parents=True, exist_ok=True)
        self.model = YOLO(str(model_path))
        self.device = device
        self.image_size = image_size
        self.bus_classes = [key for key, name in self.model.names.items() if name == "bus"]
        self.person_classes = [key for key, name in self.model.names.items() if name == "person"]
        if not self.bus_classes:
            raise ValueError("O modelo YOLO precisa conter a classe 'bus'.")

    def warmup(self):
        self.model.predict(np.zeros((384, 640, 3), dtype=np.uint8), device=self.device, imgsz=self.image_size, verbose=False)

    def reset(self):
        for tracker in getattr(self.model.predictor, "trackers", []):
            tracker.reset()

    def detect(self, frame, include_people=False) -> list[Detection]:
        classes = self.bus_classes + self.person_classes if include_people else self.bus_classes
        result = self.model.track(
            frame, persist=True, tracker="bytetrack.yaml", classes=classes,
            conf=0.25, iou=0.5, imgsz=self.image_size, device=self.device, verbose=False,
        )[0]
        if result.boxes is None or result.boxes.id is None:
            return []
        height, width = frame.shape[:2]
        detections = []
        for bbox, track_id, confidence, category in zip(
            result.boxes.xyxy.cpu().tolist(), result.boxes.id.cpu().tolist(), result.boxes.conf.cpu().tolist(),
            result.boxes.cls.cpu().tolist(),
        ):
            x1, y1, x2, y2 = map(int, bbox)
            box = (max(0, x1), max(0, y1), min(width, x2), min(height, y2))
            kind = self.model.names[int(category)]
            minimum = (8, 20) if kind == "person" else (60, 60)
            if box[2] - box[0] >= minimum[0] and box[3] - box[1] >= minimum[1]:
                detections.append(Detection(int(track_id), box, float(confidence), kind))
        return detections
