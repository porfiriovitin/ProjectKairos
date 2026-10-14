import { Icon } from "@/shared/ui/Icon";
import { labels } from "../model/constants";
import type { TravelItem } from "../model/selectors";
import styles from "./TripList.module.css";
import common from "@/shared/ui/Panel.module.css";
import { cn } from "@/shared/lib/cn";

export function TripList({
  travels,
  onSelectDestination,
}: {
  travels: TravelItem[];
  onSelectDestination: (destination: string) => void;
}) {
  return (
    <div className={styles["trip-list"]}>
      {travels.length ? (
        travels.map(({ bus, event, passengerCount: count }) => {
          return (
            <button
              data-testid="trip"
              className={styles["trip-row"]}
              key={bus.bus_code}
              onClick={() => {
                onSelectDestination(bus.itinerary.to);
              }}
            >
              <div
                className={cn(styles.platform, event && styles["has-event"])}
              >
                <span>PLAT.</span>
                <strong>{bus.boarding_platform}</strong>
              </div>
              <div className={styles["trip-route"]}>
                <strong>{bus.itinerary.to}</strong>
                <span>
                  {bus.itinerary.from} · {bus.bus_company} · {bus.bus_prefix}
                </span>
              </div>
              <div className={styles["trip-time"]}>
                <strong>{bus.itinerary.departure_time}</strong>
                <span>{count} passageiros</span>
              </div>
              <span
                className={cn(styles["status-pill"], event && styles.observed)}
              >
                {event ? labels[event.event] : "Programado"}
              </span>
              <Icon name="arrow" size={16} />
            </button>
          );
        })
      ) : (
        <div className={common["empty-state"]}>
          <Icon name="bus" size={30} />
          <h3>Nenhuma viagem disponível</h3>
          <p>
            As viagens serão exibidas quando a programação estiver disponível.
          </p>
        </div>
      )}
    </div>
  );
}
