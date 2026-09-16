"""MP4 com relógio de reprodução ou câmera com buffer de um único frame."""

from pathlib import Path
from threading import Event, Lock, Thread
from time import perf_counter, sleep

import cv2

from config import DEFAULT_VIDEO, project_path


class VideoSource:
    def __init__(self, source: str, offline=False):
        self.live = source.isdigit() or source.lower().startswith(("rtsp://", "http://", "https://"))
        self.demo = not self.live and project_path(source).resolve() == DEFAULT_VIDEO.resolve()
        self.offline = offline
        if self.live and offline:
            raise ValueError("--offline só está disponível para arquivos de vídeo.")
        target = int(source) if source.isdigit() else source if self.live else str(project_path(source))
        if not self.live and not Path(target).is_file():
            raise ValueError(f"Vídeo não encontrado: {target}")
        self.capture = cv2.VideoCapture(target)
        if not self.capture.isOpened():
            raise ValueError("Não foi possível abrir a fonte de vídeo.")
        self.fps = self.capture.get(cv2.CAP_PROP_FPS)
        if not 1 <= self.fps <= 240:
            self.fps = 30.0
        self.frame_count = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT)) if not self.live else 0
        self.duration = self.frame_count / self.fps
        self.index = -1
        self.skipped = 0
        self.started = None
        self.pause_seconds = 0.0
        self.stop = Event()
        self.lock = Lock()
        self.latest = None
        self.thread = None
        self.error = None

    def _capture_live(self):
        sequence = 0
        while not self.stop.is_set():
            success, frame = self.capture.read()
            if not success:
                self.error = "A câmera desconectou ou interrompeu a transmissão."
                self.stop.set()
                return
            with self.lock:
                self.latest = (sequence, perf_counter() - self.started, frame)
            sequence += 1

    def read(self):
        if self.started is None:
            self.started = perf_counter()
            if self.live:
                self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.thread = Thread(target=self._capture_live, daemon=True, name="boarding-capture")
                self.thread.start()
        if self.live:
            while not self.stop.is_set():
                with self.lock:
                    packet = self.latest
                if packet is not None and packet[0] != self.index:
                    self.skipped += max(0, packet[0] - self.index - 1)
                    self.index = packet[0]
                    return packet[2], packet[1]
                sleep(0.002)
            if self.error:
                raise RuntimeError(self.error)
            return None
        if not self.offline:
            elapsed = perf_counter() - self.started - self.pause_seconds
            target = max(self.index + 1, int(elapsed * self.fps))
            while self.index + 1 < target:
                if not self.capture.grab():
                    return None
                self.index += 1
                self.skipped += 1
            delay = (self.index + 1) / self.fps - elapsed
            if delay > 0:
                sleep(min(delay, 1 / self.fps))
        success, frame = self.capture.read()
        if not success:
            return None
        self.index += 1
        return frame, self.index / self.fps

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=2)
        self.capture.release()
