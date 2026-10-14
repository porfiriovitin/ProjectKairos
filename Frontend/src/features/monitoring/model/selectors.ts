import type { BoardingEvent, Bus, Passenger, Snapshot } from "./types";

export type PassengerFilter = "all" | "notified" | "waiting";
export interface TravelItem {
  bus: Bus;
  event?: BoardingEvent;
  passengerCount: number;
}
export interface PassengerItem {
  passenger: Passenger;
  bus?: Bus;
  last?: BoardingEvent;
}
export interface NotificationRecipient {
  code: string;
  name: string;
  seat?: string;
}
export interface NotificationItem {
  event: BoardingEvent;
  platform?: string;
  recipients: NotificationRecipient[];
}
export interface OperationSummaryModel {
  notifications: number;
  notifiedPassengers: number;
  totalPassengers: number;
  activeTrips: number;
  totalTrips: number;
  openBoardings: number;
}

export function selectActivity(data: Snapshot) {
  const buses = new Map(data.buses.map((bus) => [bus.bus_code, bus]));
  const passengers = new Map(
    data.passengers.map((passenger) => [passenger.passenger_code, passenger]),
  );
  const latestByBus = new Map<string, BoardingEvent>();
  const latestByPassenger = new Map<string, BoardingEvent>();
  const passengerCounts = new Map<string, number>();
  for (const passenger of data.passengers)
    passengerCounts.set(
      passenger.bus_code,
      (passengerCounts.get(passenger.bus_code) ?? 0) + 1,
    );
  for (const event of data.events) {
    latestByBus.set(event.bus_code, event);
    for (const code of event.passenger_codes)
      latestByPassenger.set(code, event);
  }
  const summary: OperationSummaryModel = {
    notifications: data.events.reduce(
      (sum, event) => sum + event.passenger_codes.length,
      0,
    ),
    notifiedPassengers: latestByPassenger.size,
    totalPassengers: passengers.size,
    activeTrips: latestByBus.size,
    totalTrips: buses.size,
    openBoardings: data.buses.filter(
      (bus) => latestByBus.get(bus.bus_code)?.event === "BOARDING_STARTED",
    ).length,
  };
  return {
    buses,
    passengers,
    latestByBus,
    latestByPassenger,
    passengerCounts,
    summary,
  };
}

export function selectNotification(
  activity: ReturnType<typeof selectActivity>,
  event: BoardingEvent,
): NotificationItem {
  return {
    event,
    platform:
      event.platform ?? activity.buses.get(event.bus_code)?.boarding_platform,
    recipients: event.passenger_codes.map((code) => {
      const passenger = activity.passengers.get(code);
      return { code, name: passenger?.name ?? code, seat: passenger?.seat };
    }),
  };
}

export function selectMonitoringView(
  data: Snapshot,
  activity: ReturnType<typeof selectActivity>,
  filters: {
    platform: string;
    query: string;
    passengerStatus: PassengerFilter;
  },
) {
  const matchesPlatform = (platform?: string) =>
    filters.platform === "all" || platform === filters.platform;
  const query = filters.query.trim().toLocaleLowerCase("pt-BR");
  const travels = data.buses
    .filter((bus) => matchesPlatform(bus.boarding_platform))
    .map((bus) => ({
      bus,
      event: activity.latestByBus.get(bus.bus_code),
      passengerCount: activity.passengerCounts.get(bus.bus_code) ?? 0,
    }));
  const passengers = data.passengers
    .map((passenger) => ({
      passenger,
      bus: activity.buses.get(passenger.bus_code),
      last: activity.latestByPassenger.get(passenger.passenger_code),
    }))
    .filter(
      ({ passenger, bus, last }) =>
        matchesPlatform(bus?.boarding_platform) &&
        (filters.passengerStatus === "all" ||
          Boolean(last) === (filters.passengerStatus === "notified")) &&
        `${passenger.name} ${passenger.passenger_code} ${bus?.itinerary.to ?? ""}`
          .toLocaleLowerCase("pt-BR")
          .includes(query),
    );
  const notifications = data.events
    .map((event) => selectNotification(activity, event))
    .filter((item) => matchesPlatform(item.platform));
  return {
    travels,
    passengers,
    notifications,
    events: notifications.map((item) => item.event),
  };
}
