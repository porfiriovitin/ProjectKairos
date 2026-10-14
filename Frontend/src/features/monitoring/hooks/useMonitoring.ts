import { useEffect, useState } from "react";
import { getMonitoringEndpoint } from "@/config/environment";
import { createMonitoringClient } from "../api/monitoringClient";
import type { ConnectionStatus } from "../api/monitoringClient";
import { empty } from "../model/constants";
import { createFrameStore } from "../model/frameStore";

export function useMonitoring() {
  const [endpoint] = useState(getMonitoringEndpoint);
  const [frameStore] = useState(createFrameStore);
  const [data, setData] = useState(empty);
  const [connection, setConnection] = useState<ConnectionStatus>("connecting");
  const [error, setError] = useState("");

  useEffect(() => {
    const client = createMonitoringClient(endpoint, {
      onConnection: setConnection,
      onError: setError,
      onMessage: (message) => {
        switch (message.type) {
          case "snapshot":
            frameStore.replace(message.payload.frames);
            setData({ ...message.payload, frames: {} });
            setError("");
            break;
          case "event":
            setData((current) =>
              current.events.some((event) => event.id === message.payload.id)
                ? current
                : { ...current, events: [...current.events, message.payload] },
            );
            break;
          case "status":
            setData((current) => ({ ...current, status: message.payload }));
            break;
          case "frame":
            frameStore.update(message.payload);
            break;
        }
      },
    });
    client.start();
    return client.stop;
  }, [endpoint, frameStore]);

  return { data, connection, error, frameStore };
}
