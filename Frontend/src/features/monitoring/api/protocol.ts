import type {
  BoardingEvent,
  Bus,
  Frame,
  Passenger,
  Snapshot,
} from "../model/types";
import { labels } from "../model/constants";

export type MonitoringMessage =
  | { type: "snapshot"; payload: Snapshot }
  | { type: "event"; payload: BoardingEvent }
  | { type: "frame"; payload: Frame }
  | { type: "status"; payload: string };

type RecordValue = Record<string, unknown>;
const object = (value: unknown): value is RecordValue =>
  !!value && typeof value === "object" && !Array.isArray(value);
const strings = (value: RecordValue, fields: string[]) =>
  fields.every((field) => typeof value[field] === "string");
const number = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value);
const itinerary = (value: unknown): value is Bus["itinerary"] =>
  object(value) && strings(value, ["from", "to", "departure_time"]);
function bus(value: unknown): value is Bus {
  return (
    object(value) &&
    strings(value, [
      "bus_code",
      "bus_company",
      "bus_prefix",
      "boarding_platform",
      "bus_kind",
    ]) &&
    itinerary(value.itinerary)
  );
}
function passenger(value: unknown): value is Passenger {
  return (
    object(value) &&
    strings(value, [
      "passenger_code",
      "name",
      "bus_code",
      "ticket_code",
      "seat",
    ]) &&
    typeof value.has_checked_in === "boolean"
  );
}
function event(value: unknown): value is BoardingEvent {
  return (
    object(value) &&
    strings(value, [
      "id",
      "event",
      "bus_code",
      "bus_company",
      "bus_prefix",
      "message",
      "emitted_at",
    ]) &&
    Object.hasOwn(labels, value.event as string) &&
    itinerary(value.itinerary) &&
    number(value.video_seconds) &&
    Array.isArray(value.passenger_codes) &&
    value.passenger_codes.every((code) => typeof code === "string") &&
    (value.platform === undefined || typeof value.platform === "string")
  );
}
function frame(value: unknown): value is Frame {
  return (
    object(value) &&
    (value.scene === "arrival" || value.scene === "boarding") &&
    typeof value.image === "string" &&
    value.image.startsWith("data:image/jpeg;base64,") &&
    number(value.seconds)
  );
}
function snapshot(value: unknown): value is Snapshot {
  return (
    object(value) &&
    strings(value, ["session_id", "date", "status"]) &&
    Array.isArray(value.buses) &&
    value.buses.every(bus) &&
    Array.isArray(value.passengers) &&
    value.passengers.every(passenger) &&
    Array.isArray(value.events) &&
    value.events.every(event) &&
    (value.frames === undefined ||
      (object(value.frames) &&
        Object.entries(value.frames).every(
          ([scene, image]) => frame(image) && image.scene === scene,
        )))
  );
}

export function parseMonitoringMessage(raw: unknown): MonitoringMessage {
  if (typeof raw !== "string") throw new Error("Formato de mensagem inválido.");
  const message: unknown = JSON.parse(raw);
  if (!object(message)) throw new Error("Mensagem inválida.");
  const payload = message.payload;
  switch (message.type) {
    case "snapshot":
      if (snapshot(payload))
        return {
          type: "snapshot",
          payload: { ...payload, frames: payload.frames ?? {} },
        };
      break;
    case "event":
      if (event(payload)) return { type: "event", payload };
      break;
    case "frame":
      if (frame(payload)) return { type: "frame", payload };
      break;
    case "status":
      if (typeof payload === "string") return { type: "status", payload };
      break;
  }
  throw new Error("Mensagem incompatível com o contrato de monitoramento.");
}
