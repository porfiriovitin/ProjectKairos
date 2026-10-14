"""Codifica somente a imagem mais recente, fora da thread de inferência."""

import base64
from threading import Condition, Thread
from time import perf_counter

import cv2


class FrameStream:
    def __init__(self, publish, fps=20, width=960, quality=75):
        self.publish = publish
        self.interval = 1 / fps
        self.width = width
        self.quality = quality
        self.condition = Condition()
        self.latest = None
        self.stopped = False
        self.sent = 0
        self.replaced = 0
        self.thread = Thread(target=self._encode, name="dashboard-jpeg", daemon=True)
        self.thread.start()

    def submit(self, scene, frame, seconds):
        # O overlay devolve um array novo que não será alterado pela inferência.
        with self.condition:
            if self.stopped:
                return
            if self.latest is not None:
                self.replaced += 1
            self.latest = (scene, frame, seconds)
            self.condition.notify()

    def _encode(self):
        next_frame = 0.0
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.stopped or self.latest is not None)
                if self.stopped and self.latest is None:
                    return
                delay = next_frame - perf_counter()
                if delay > 0 and not self.stopped:
                    self.condition.wait(timeout=delay)
                    continue
                scene, frame, seconds = self.latest
                self.latest = None
            next_frame = perf_counter() + self.interval
            if frame.shape[1] > self.width:
                frame = cv2.resize(frame, (self.width, round(frame.shape[0] * self.width / frame.shape[1])), interpolation=cv2.INTER_AREA)
            ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
            if ok:
                image = "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii")
                self.publish(scene, image, seconds)
                self.sent += 1

    def close(self):
        with self.condition:
            self.stopped = True
            self.condition.notify()
        self.thread.join(timeout=5)
