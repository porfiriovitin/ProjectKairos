"""Mede os frames recebidos pelo socket local, sem interferir na inferência."""
import argparse
import base64
import json
from time import perf_counter, sleep

import cv2
import numpy as np
from websockets.sync.client import connect


parser = argparse.ArgumentParser()
parser.add_argument("--url", default="ws://127.0.0.1:8765")
parser.add_argument("--seconds", type=float, default=8)
args = parser.parse_args()
received = []
last = None
deadline = perf_counter() + 30
while True:
    try:
        client = connect(args.url, open_timeout=1)
        break
    except (OSError, TimeoutError):
        if perf_counter() >= deadline:
            raise
        sleep(.1)
with client:
    snapshot = json.loads(client.recv(timeout=5))
    if snapshot["type"] != "snapshot":
        raise RuntimeError("O servidor não enviou o snapshot inicial.")
    started = perf_counter()
    while perf_counter() - started < args.seconds:
        try:
            message = json.loads(client.recv(timeout=max(.01, args.seconds - (perf_counter() - started))))
        except TimeoutError:
            break
        if message["type"] == "frame":
            received.append(perf_counter())
            last = message["payload"]
elapsed = perf_counter() - started
report = {"received_frames": len(received), "seconds": round(elapsed, 3), "received_fps": round(len(received) / elapsed, 2)}
if last:
    jpeg = base64.b64decode(last["image"].split(",", 1)[1])
    image = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    report["image_size"] = [image.shape[1], image.shape[0]]
    report["scene"] = last["scene"]
print(json.dumps(report, ensure_ascii=False))
if len(received) < 3:
    raise SystemExit("Poucos frames recebidos: confira se o vídeo ainda está sendo processado.")
