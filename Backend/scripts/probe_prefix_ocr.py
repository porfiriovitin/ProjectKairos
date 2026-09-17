"""Diagnóstico de prefixos: localização e OCR reais, sem fornecer a resposta."""

import sys
from pathlib import Path

import cv2
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from config import prepare_environment

prepare_environment()
from vision.detector import BusDetector
from vision.ocr_reader import OCRReader

torch.set_num_threads(2)
cv2.setNumThreads(1)
device = "0" if torch.cuda.is_available() else "cpu"
detector = BusDetector(ROOT / "models/yolo11n.pt", device, 640)
reader = OCRReader(ROOT / "models/easyocr", device)
capture = cv2.VideoCapture(str(ROOT / "src/videos/OnibusDandoEmbarque.mp4"))
try:
    for timestamp in (0, 16, 24, 40, 56, 80):
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ok, original = capture.read()
        if not ok:
            continue
        frame = cv2.resize(original, (1280, 720))
        detector.reset()
        for detection in detector.detect(frame):
            x1, y1, x2, y2 = detection.bbox
            if y2 < 460 or x2 - x1 < 120:
                continue
            result = reader.read(frame, detection, timestamp, prefix_frame=original)
            print(timestamp, detection.bbox, [(r.text, round(r.confidence, 3)) for r in result.readings if r.kind == "PREFIXO"], flush=True)
finally:
    capture.release()
    reader.close()
