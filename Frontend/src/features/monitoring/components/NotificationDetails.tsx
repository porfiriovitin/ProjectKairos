import { useEffect, useRef } from "react";
import { Icon } from "@/shared/ui/Icon";
import { labels } from "../model/constants";
import { eventTime } from "../lib/eventTime";
import type { NotificationItem } from "../model/selectors";
import styles from "./NotificationDetails.module.css";
import common from "@/shared/ui/Panel.module.css";

export function NotificationDetails({
  notification,
  onClose,
}: {
  notification: NotificationItem | null;
  onClose: () => void;
}) {
  const selected = notification?.event;
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (selected) ref.current?.showModal();
    else ref.current?.close();
  }, [selected]);
  return (
    <dialog
      className={styles.dialog}
      ref={ref}
      onCancel={onClose}
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
      aria-labelledby="dialog-title"
    >
      <div className={styles["dialog-heading"]}>
        <h2 id="dialog-title">{selected ? labels[selected.event] : ""}</h2>
        <button
          className={common["icon-button"]}
          aria-label="Fechar"
          onClick={onClose}
        >
          <Icon name="close" />
        </button>
      </div>
      {selected && (
        <>
          <p className={styles["dialog-route"]}>
            {selected.bus_company} · {selected.itinerary.from} →{" "}
            {selected.itinerary.to}
          </p>
          <blockquote>{selected.message}</blockquote>
          <div className={styles["event-meta"]}>
            <span>
              Viagem<strong>{selected.bus_code}</strong>
            </span>
            <span>
              Plataforma
              <strong>{notification?.platform ?? "—"}</strong>
            </span>
            <span>
              Horário do registro<strong>{eventTime(selected)}</strong>
            </span>
          </div>
          <h3>Destinatários</h3>
          <div className={styles["recipient-list"]}>
            {notification?.recipients.length ? (
              notification.recipients.map((recipient) => (
                <div key={recipient.code}>
                  <span className={common["avatar"]}>{recipient.name[0]}</span>
                  <div>
                    <strong>{recipient.name}</strong>
                    <small>
                      {recipient.code} · Assento {recipient.seat ?? "—"}
                    </small>
                  </div>
                </div>
              ))
            ) : (
              <p>Nenhum passageiro vinculado a esta notificação.</p>
            )}
          </div>
        </>
      )}
    </dialog>
  );
}
