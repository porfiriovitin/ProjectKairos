"""OCR assíncrono limitado a um trabalho; não acumula atraso no vídeo."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import perf_counter

import cv2
import easyocr
import numpy as np


@dataclass
class TextReading:
    text: str
    confidence: float
    polygon: list
    kind: str | None = None


@dataclass
class OCRResult:
    track_id: int
    timestamp: float
    bbox: tuple
    readings: list[TextReading]
    gray: np.ndarray
    seconds: float


class OCRReader:
    def __init__(self, model_directory, device="cpu"):
        model_directory.mkdir(parents=True, exist_ok=True)
        gpu = False if device == "cpu" else f"cuda:{device}" if device.isdigit() else device
        self.reader = easyocr.Reader(
            ["pt", "en"], gpu=gpu, model_storage_directory=str(model_directory),
            user_network_directory=str(model_directory / "user_network"), verbose=False,
        )
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="boarding-ocr")
        self.future = None
        self.calls = 0
        self.seconds = 0.0

    def read(self, frame, detection, timestamp, other_boxes=(), prefix_frame=None) -> OCRResult:
        start = perf_counter()
        x1, y1, x2, y2 = detection.bbox
        crop = frame[y1:y2, x1:x2].copy()
        # Retire da amostra regiões pertencentes a outros ônibus, evitando misturar identidades.
        for ox1, oy1, ox2, oy2 in other_boxes:
            left, top = max(x1, ox1) - x1, max(y1, oy1) - y1
            right, bottom = min(x2, ox2) - x1, min(y2, oy2) - y1
            if right > left and bottom > top:
                crop[top:bottom, left:right] = 0
        scale = min(1.5, 1000 / max(crop.shape[:2]))
        enlarged = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        results = self.reader.readtext(
            enlarged, detail=1, paragraph=False, decoder="greedy", batch_size=1,
            workers=0, min_size=8, text_threshold=0.55, low_text=0.3,
            link_threshold=0.35, canvas_size=1280, mag_ratio=1.0,
        )
        readings = []
        for polygon, text, confidence in results:
            if confidence < 0.15 or len(text.strip()) < 2:
                continue
            points = [[float(px / scale + x1), float(py / scale + y1)] for px, py in polygon]
            readings.append(TextReading(text.strip(), float(confidence), points))
        if prefix_frame is not None:
            from vision.prefix_region import locate_prefix

            sx, sy = prefix_frame.shape[1] / frame.shape[1], prefix_frame.shape[0] / frame.shape[0]
            bounds = locate_prefix(prefix_frame, (int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy)))
            if bounds is not None:
                left, top, right, bottom = bounds
                patch = prefix_frame[top:bottom, left:right]
                patch = cv2.resize(patch, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
                candidates = self.reader.recognize(cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY), allowlist="0123456789", detail=1)
                _, text, confidence = max(candidates, key=lambda item: item[2], default=(None, "", 0.0))
                points = [[left / sx, top / sy], [right / sx, top / sy], [right / sx, bottom / sy], [left / sx, bottom / sy]]
                readings.append(TextReading(text.strip(), float(confidence), points, "PREFIXO"))
        return OCRResult(
            detection.track_id, timestamp, detection.bbox, readings,
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), perf_counter() - start,
        )

    @property
    def busy(self):
        return self.future is not None

    def submit(self, frame, detection, timestamp, other_boxes=(), prefix_frame=None):
        if self.busy:
            return False
        self.future = self.executor.submit(self.read, frame.copy(), detection, timestamp, other_boxes, prefix_frame)
        return True

    def poll(self, wait=False):
        if self.future is None or (not wait and not self.future.done()):
            return None
        future, self.future = self.future, None
        result = future.result()
        self.calls += 1
        self.seconds += result.seconds
        return result

    def close(self):
        self.executor.shutdown(wait=True, cancel_futures=True)
