"""Localiza a numeração escura na faixa amarela frontal desta câmera.

Não recebe o prefixo esperado: a localização não depende da programação.
"""

import cv2


def locate_prefix(frame, bbox):
    x1, y1, x2, y2 = bbox
    top = int(y1 + (y2 - y1) * 0.65)
    crop = frame[top:y2, x1:x2]
    if crop.size == 0 or min(crop.shape[:2]) < 21:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    yellow = cv2.inRange(hsv, (18, 65, 85), (40, 255, 255))
    contours, _ = cv2.findContours(yellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) < crop.shape[0] * crop.shape[1] * 0.015:
        return None
    mask = yellow * 0
    cv2.drawContours(mask, [contour], -1, 255, -1)
    mask = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    dark = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 9) & mask
    glyphs, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in glyphs if cv2.contourArea(c) > 3]
    boxes = [b for b in boxes if 3 <= b[3] <= crop.shape[0] * 0.4 and b[2] <= crop.shape[1] * 0.2]
    if len(boxes) < 3:
        return None
    left = max(0, min(b[0] for b in boxes) - 3)
    upper = max(0, min(b[1] for b in boxes) - 3)
    right = min(crop.shape[1], max(b[0] + b[2] for b in boxes) + 3)
    bottom = min(crop.shape[0], max(b[1] + b[3] for b in boxes) + 3)
    if not 1.8 <= (right - left) / max(bottom - upper, 1) <= 10:
        return None
    return x1 + left, top + upper, x1 + right, top + bottom
