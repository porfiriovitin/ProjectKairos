"""WebSocket local: snapshot consistente, eventos ordenados e clientes isolados."""

import asyncio
import json
import threading
from datetime import datetime, timezone
from uuid import uuid4


class DashboardSocket:
    def __init__(self, date, buses, passengers, host="127.0.0.1", port=8765):
        self.host, self.port = host, port
        self.session_id = str(uuid4())
        self.state = {"session_id": self.session_id, "date": date, "buses": buses,
                      "passengers": passengers, "events": [], "status": "processing",
                      "data_source": "repository_demo", "frames": {}}
        self.clients = {}
        self.ready = threading.Event()
        self.error = None
        self.loop = None
        self.stop_event = None
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run, name="dashboard-websocket", daemon=True)
        self.thread.start()
        if not self.ready.wait(10):
            raise RuntimeError("Tempo excedido ao iniciar o WebSocket.")
        if self.error:
            raise RuntimeError(f"Não foi possível iniciar o WebSocket: {self.error}") from self.error
        print(f"[PAINEL] ws://{self.host}:{self.port} | abra o frontend", flush=True)

    def _run(self):
        try:
            asyncio.run(self._serve())
        except Exception as error:
            self.error = error
            self.ready.set()

    async def _serve(self):
        from websockets.asyncio.server import serve
        self.loop = asyncio.get_running_loop()
        self.stop_event = asyncio.Event()
        async with serve(self._handle, self.host, self.port, max_size=4096, close_timeout=2) as server:
            self.port = server.sockets[0].getsockname()[1]
            self.ready.set()
            await self.stop_event.wait()

    async def _handle(self, socket):
        queue = asyncio.Queue(maxsize=128)
        frames = {}
        ready = asyncio.Event()
        # O snapshot e o registro do cliente ocorrem no mesmo turno do loop.
        queue.put_nowait(json.dumps({"type": "snapshot", "payload": self.state}, ensure_ascii=False))
        self.clients[socket] = (queue, frames, ready)
        ready.set()

        async def send():
            while True:
                await ready.wait()
                if not queue.empty():
                    message = queue.get_nowait()
                elif frames:
                    _, message = frames.popitem()
                else:
                    ready.clear()
                    continue
                await socket.send(message)

        writer = asyncio.create_task(send())
        closed = asyncio.create_task(socket.wait_closed())
        try:
            await asyncio.wait([writer, closed], return_when=asyncio.FIRST_COMPLETED)
        finally:
            self.clients.pop(socket, None)
            writer.cancel()
            closed.cancel()
            await asyncio.gather(writer, closed, return_exceptions=True)

    def _broadcast(self, message):
        encoded = json.dumps(message, ensure_ascii=False)
        for socket, (queue, frames, ready) in list(self.clients.items()):
            if message["type"] == "frame":
                # Substitua o frame pendente: nunca reproduza uma fila atrasada.
                frames[message["payload"]["scene"]] = encoded
            elif queue.full():
                # Um navegador lento não bloqueia a análise de vídeo.
                asyncio.create_task(socket.close(code=1013, reason="Reconecte para receber o histórico."))
            else:
                queue.put_nowait(encoded)
            ready.set()

    def publish(self, event):
        event = {**event, "emitted_at": datetime.now(timezone.utc).isoformat()}

        def append():
            event["id"] = f"{self.session_id}:{len(self.state['events']) + 1}"
            self.state["events"].append(event)
            self._broadcast({"type": "event", "payload": event})

        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(append)

    def set_status(self, status):
        def update():
            self.state["status"] = status
            self._broadcast({"type": "status", "payload": status})
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(update)

    def close(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.stop_event.set)
        if self.thread:
            self.thread.join(timeout=5)

    def publish_frame(self, scene, image, seconds):
        frame = {"scene": scene, "image": image, "seconds": round(seconds, 2)}
        def update():
            self.state["frames"][scene] = frame
            self._broadcast({"type": "frame", "payload": frame})
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(update)
