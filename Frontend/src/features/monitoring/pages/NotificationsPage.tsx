import { Icon } from "@/shared/ui/Icon";
import { labels } from "../model/constants";
import { eventTime } from "../lib/eventTime";
import type { BoardingEvent } from "../model/types";
import styles from "./NotificationsPage.module.css";
import common from "@/shared/ui/Panel.module.css";

export function NotificationsPage({
  events,
  onSelect,
}: {
  events: BoardingEvent[];
  onSelect: (event: BoardingEvent) => void;
}) {
  return (
    <section>
      <div className={common["section-heading"]}>
        <h2>Avisos registrados</h2>
        <span>{events.length} registros</span>
      </div>
      <div data-testid="event-history" className={styles["event-history"]}>
        {[...events].reverse().map((event) => (
          <button key={event.id} onClick={() => onSelect(event)}>
            <span className={styles["event-symbol"]}>
              <Icon name={event.event === "BUS_ARRIVED" ? "bus" : "bell"} />
            </span>
            <div>
              <strong>{labels[event.event]}</strong>
              <p>{event.message}</p>
              <small>
                {event.bus_company} · {event.itinerary.to} ·{" "}
                {event.passenger_codes.length} destinatários
              </small>
            </div>
            <span>{eventTime(event)}</span>
          </button>
        ))}
        {!events.length && (
          <div className={common["empty-state"]}>
            <Icon name="bell" size={30} />
            <h3>Nenhuma notificação registrada</h3>
            <p>Os avisos serão exibidos conforme a movimentação das viagens.</p>
          </div>
        )}
      </div>
    </section>
  );
}
