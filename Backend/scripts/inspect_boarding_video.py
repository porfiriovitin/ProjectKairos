"""Gera uma folha de contato para calibrar a câmera de embarque."""

from pathlib import Path

import cv2
import numpy as np

root = Path(__file__).resolve().parents[1]
capture = cv2.VideoCapture(str(root / "src/videos/OnibusDandoEmbarque.mp4"))
times = [0, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 94]
sheet = np.zeros((4 * 295, 4 * 480, 3), dtype=np.uint8)
for index, timestamp in enumerate(times):
    capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
    success, frame = capture.read()
    if not success:
        continue
    frame = cv2.resize(frame, (480, 270))
    row, column = divmod(index, 4)
    y, x = row * 295, column * 480
    sheet[y:y + 270, x:x + 480] = frame
    cv2.putText(sheet, f"{timestamp}s", (x + 8, y + 290), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
capture.release()
destination = root / "outputs/boarding-contact-sheet.jpg"
destination.parent.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(destination), sheet)
print(destination)
