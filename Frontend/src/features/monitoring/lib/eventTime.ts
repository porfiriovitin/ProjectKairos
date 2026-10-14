import type { BoardingEvent } from "../model/types";
export function eventTime(event: BoardingEvent) {
  const date = new Date(event.emitted_at);
  return Number.isNaN(date.getTime())
    ? "—"
    : new Intl.DateTimeFormat("pt-BR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(date);
}
