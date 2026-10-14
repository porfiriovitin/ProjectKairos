import type { EventKind, Snapshot } from "./types";
export const labels: Record<EventKind, string> = {
  BUS_ARRIVED: "Chegada confirmada",
  BUS_AT_PLATFORM: "Na plataforma",
  BUS_PARKED: "Ônibus estacionado",
  BOARDING_STARTED: "Embarque iniciado",
  BOARDING_FINISHED: "Embarque encerrado",
  BUS_DEPARTED: "Ônibus partiu",
};
export const empty: Snapshot = {
  session_id: "",
  date: "",
  buses: [],
  passengers: [],
  events: [],
  frames: {},
  status: "waiting",
};
