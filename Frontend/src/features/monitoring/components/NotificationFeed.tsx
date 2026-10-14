import { Icon } from "@/shared/ui/Icon";
import { labels } from "../model/constants";
import { eventTime } from "../lib/eventTime";
import type { BoardingEvent } from "../model/types";
import type { NotificationItem } from "../model/selectors";
import styles from "./NotificationFeed.module.css";
import { cn } from "@/shared/lib/cn";

export function NotificationFeed({
  notifications,
  date,
  onSelect,
}: {
  notifications: NotificationItem[];
  date: string;
  onSelect: (event: BoardingEvent) => void;
}) {
  return (
    <aside className={styles["feed"]}>
      <div
        data-testid="notification-heading"
        className={styles["feed-heading"]}
      >
        <h2>Notificações aos passageiros</h2>
        <span
          data-testid="notification-count"
          className={styles["count-badge"]}
        >
          {notifications.length}
        </span>
      </div>
      <p className={styles["feed-description"]}>
        Mensagens direcionadas aos passageiros de cada viagem.
      </p>
      <div className={styles["feed-date"]}>
        <span>{date || "Sem registros"}</span>
      </div>
      <div
        className={styles["feed-list"]}
        aria-live="polite"
        aria-relevant="additions"
      >
        {[...notifications].reverse().map(({ event, recipients }, index) => (
          <button
            data-testid="notification-card"
            className={cn(styles["feed-item"], index === 0 && styles.latest)}
            key={event.id}
            onClick={() => onSelect(event)}
          >
            <span className={styles["feed-line-dot"]} />
            <div className={styles["feed-item-top"]}>
              <span className={styles["event-label"]}>
                {labels[event.event]}
              </span>
              <span>{eventTime(event)}</span>
            </div>
            <strong>{event.itinerary.to}</strong>
            <div className={styles["feed-message"]}>
              <span className={styles["feed-message-label"]}>
                <Icon name="bell" size={13} />
                Mensagem ao passageiro
              </span>
              <p>{event.message}</p>
            </div>
            <div className={styles["feed-recipients"]}>
              <span className={styles["feed-recipient-label"]}>
                Destinatários
              </span>
              <div className={styles["feed-recipient-names"]}>
                {recipients.length ? (
                  recipients
                    .slice(0, 3)
                    .map((recipient) => (
                      <span key={recipient.code}>{recipient.name}</span>
                    ))
                ) : (
                  <span>Nenhum passageiro vinculado</span>
                )}
                {event.passenger_codes.length > 3 && (
                  <span>+ {event.passenger_codes.length - 3} passageiros</span>
                )}
              </div>
            </div>
            <div className={styles["feed-delivery"]}>
              <span>
                <Icon name="check" size={13} />
                Notificação emitida
              </span>
              <span>
                {event.passenger_codes.length}{" "}
                {event.passenger_codes.length === 1
                  ? "destinatário"
                  : "destinatários"}
                <Icon name="arrow" size={14} />
              </span>
            </div>
          </button>
        ))}
        {!notifications.length && (
          <div className={styles["feed-empty"]}>
            <div>
              <Icon name="bell" size={28} />
            </div>
            <strong>Nenhuma notificação registrada</strong>
            <p>Os avisos serão exibidos conforme a movimentação das viagens.</p>
          </div>
        )}
      </div>
    </aside>
  );
}
