import { useMemo, useState } from "react";
import {
  selectActivity,
  selectMonitoringView,
  selectNotification,
} from "../model/selectors";
import type { PassengerFilter } from "../model/selectors";
import type { BoardingEvent, Snapshot } from "../model/types";

export function useMonitoringView(data: Snapshot) {
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [passengerFilter, setPassengerFilter] =
    useState<PassengerFilter>("all");
  const [selected, setSelected] = useState<BoardingEvent | null>(null);
  const activity = useMemo(() => selectActivity(data), [data]);
  const view = useMemo(
    () =>
      selectMonitoringView(data, activity, {
        platform: filter,
        query: search,
        passengerStatus: passengerFilter,
      }),
    [data, activity, filter, search, passengerFilter],
  );
  const details = useMemo(
    () =>
      selected && data.events.some((event) => event.id === selected.id)
        ? selectNotification(activity, selected)
        : null,
    [activity, selected, data.events],
  );
  return {
    ...view,
    summary: activity.summary,
    filter,
    setFilter,
    search,
    setSearch,
    passengerFilter,
    setPassengerFilter,
    details,
    selectNotification: setSelected,
    closeNotification: () => setSelected(null),
  };
}
