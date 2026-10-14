const DEFAULT_SOCKET_URL = "ws://127.0.0.1:8765";

export function getMonitoringEndpoint(): string {
  let saved: string | null = null;
  try {
    saved = localStorage.getItem("kairos-socket");
  } catch {
    /* O armazenamento pode estar indisponível. */
  }
  return import.meta.env.VITE_WS_URL || saved || DEFAULT_SOCKET_URL;
}
