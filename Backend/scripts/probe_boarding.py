"""Verifica as regras nas imagens do vídeo, sem interface nem OCR."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import prepare_environment
prepare_environment()

import cv2
import torch
from services.boarding import BoardingMonitor, load_platforms
from services.bus_matcher import load_data
from vision.detector import BusDetector
from vision.platform_geometry import PlatformGeometry

torch.set_num_threads(2)
cv2.setNumThreads(1)
_, buses, _ = load_data(ROOT)
config = load_platforms(ROOT / "config/platforms.json", buses)
monitor = BoardingMonitor(config)
geometry = PlatformGeometry(config["platforms"])
detector = BusDetector(ROOT / "models/yolo11n.pt", "0" if torch.cuda.is_available() else "cpu", 640)
detector.warmup()
capture = cv2.VideoCapture(str(ROOT / "src/videos/OnibusDandoEmbarque.mp4"))
observations, events = [], []
for step in range(192):
    timestamp = step * 0.5
    capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
    success, frame = capture.read()
    if not success:
        break
    frame = cv2.resize(frame, (1280, 720))
    detections = detector.detect(frame, include_people=True)
    vehicles = [d for d in detections if d.kind == "bus"]
    people = [d for d in detections if d.kind == "person"]
    anchors = geometry.update(frame, timestamp)
    emitted = monitor.update(vehicles, people, anchors, timestamp, frame.shape)
    events.extend(emitted)
    entry = {"time": timestamp, "anchors": anchors, "buses": [[d.track_id, d.bbox] for d in vehicles], "people": len(people), "platforms": {p.number: {"track": p.track_id, "status": p.status, "count": p.people_count, "door": len(p.door_ids), "lost": p.lost} for p in monitor.platforms.values()}}
    observations.append(entry)
    if emitted or step % 10 == 0:
        print(json.dumps(entry), flush=True)
        for event in emitted:
            print("EVENT", event["event"], event["platform"], event["video_seconds"], flush=True)
capture.release()
path = ROOT / "outputs/boarding-probe.json"
path.parent.mkdir(parents=True, exist_ok=True)
with path.open("w", encoding="utf-8") as file:
    json.dump({"observations": observations, "events": events}, file, indent=2)
