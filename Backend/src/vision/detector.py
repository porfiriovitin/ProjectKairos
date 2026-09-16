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


class BusDetector:
    def __init__(self, model_path: Path, device: str, image_size: int):
        model_path.parent.mkdir(parents=True, exist_ok=True)
        self.model = YOLO(str(model_path))
        self.device = device
        self.image_size = image_size
        self.bus_classes = [key for key, name in self.model.names.items() if name == "bus"]
        if not self.bus_classes:
            raise ValueError("O modelo YOLO precisa conter a classe 'bus'.")

    def warmup(self):
        self.model.predict(np.zeros((384, 640, 3), dtype=np.uint8), device=self.device, imgsz=self.image_size, verbose=False)

    def detect(self, frame) -> list[Detection]:
        result = self.model.track(
            frame, persist=True, tracker="bytetrack.yaml", classes=self.bus_classes,
            conf=0.25, iou=0.5, imgsz=self.image_size, device=self.device, verbose=False,
        )[0]
        if result.boxes is None or result.boxes.id is None:
            return []
        height, width = frame.shape[:2]
        detections = []
        for bbox, track_id, confidence in zip(
            result.boxes.xyxy.cpu().tolist(), result.boxes.id.cpu().tolist(), result.boxes.conf.cpu().tolist()
        ):
            x1, y1, x2, y2 = map(int, bbox)
            box = (max(0, x1), max(0, y1), min(width, x2), min(height, y2))
            if box[2] - box[0] >= 60 and box[3] - box[1] >= 60:
                detections.append(Detection(int(track_id), box, float(confidence)))
        return detections
