import { parseMonitoringMessage } from "./protocol";
import type { MonitoringMessage } from "./protocol";

export type ConnectionStatus = "connecting" | "connected" | "disconnected";
interface ClientCallbacks {
  onMessage: (message: MonitoringMessage) => void;
  onConnection: (status: ConnectionStatus) => void;
  onError: (message: string) => void;
}

export function createMonitoringClient(
  endpoint: string,
  callbacks: ClientCallbacks,
) {
  let disposed = false;
  let socket: WebSocket | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let attempt = 0;

  function connect() {
    if (disposed) return;
    callbacks.onConnection("connecting");
    try {
      socket = new WebSocket(endpoint);
    } catch {
      callbacks.onConnection("disconnected");
      callbacks.onError("Não foi possível acessar o monitoramento.");
      return;
    }
    socket.onopen = () => {
      if (disposed) return;
      attempt = 0;
      callbacks.onConnection("connected");
      callbacks.onError("");
    };
    socket.onmessage = (message) => {
      if (disposed) return;
      try {
        callbacks.onMessage(parseMonitoringMessage(message.data));
      } catch {
        callbacks.onError(
          "Não foi possível atualizar os registros de monitoramento.",
        );
      }
    };
    socket.onerror = () => {
      if (!disposed)
        callbacks.onError(
          "Atualizações temporariamente indisponíveis. Tentando novamente…",
        );
    };
    socket.onclose = () => {
      if (disposed) return;
      callbacks.onConnection("disconnected");
      timer = setTimeout(connect, Math.min(1000 * 2 ** attempt++, 10000));
    };
  }

  return {
    start: () => {
      timer = setTimeout(connect, 0);
    },
    stop: () => {
      disposed = true;
      clearTimeout(timer);
      if (socket) {
        socket.onopen =
          socket.onmessage =
          socket.onerror =
          socket.onclose =
            null;
        socket.close();
      }
    },
  };
}
