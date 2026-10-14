export type EventKind =
  | "BUS_ARRIVED"
  | "BUS_AT_PLATFORM"
  | "BUS_PARKED"
  | "BOARDING_STARTED"
  | "BOARDING_FINISHED"
  | "BUS_DEPARTED";
export interface Bus {
  bus_code: string;
  bus_company: string;
  bus_prefix: string;
  boarding_platform: string;
  bus_kind: string;
  itinerary: { from: string; to: string; departure_time: string };
}
export interface Passenger {
  passenger_code: string;
  name: string;
  bus_code: string;
  ticket_code: string;
  seat: string;
  has_checked_in: boolean;
}
export interface BoardingEvent {
  id: string;
  event: EventKind;
  bus_code: string;
  bus_company: string;
  bus_prefix: string;
  itinerary: Bus["itinerary"];
  passenger_codes: string[];
  platform?: string;
  people_count?: number;
  message: string;
  video_seconds: number;
  sequence_seconds?: number;
  emitted_at: string;
  identity_source?: string;
}
export interface Frame {
  scene: "arrival" | "boarding";
  image: string;
  seconds: number;
}
export interface Snapshot {
  session_id: string;
  date: string;
  buses: Bus[];
  passengers: Passenger[];
  events: BoardingEvent[];
  frames: Partial<Record<Frame["scene"], Frame>>;
  status: string;
}
