import { Icon } from "@/shared/ui/Icon";
import type { OperationSummaryModel } from "../model/selectors";
import styles from "./OperationSummary.module.css";
import { cn } from "@/shared/lib/cn";

export function OperationSummary({
  summary,
}: {
  summary: OperationSummaryModel;
}) {
  return (
    <section className={styles["metrics"]} aria-label="Resumo da operação">
      <div className={cn(styles["metric"], styles["lead"])}>
        <span>Notificações registradas</span>
        <strong data-testid="total-notifications">
          {summary.notifications.toString().padStart(2, "0")}
          <Icon name="bell" size={24} />
        </strong>
        <small>Total de avisos por passageiro</small>
      </div>
      <div className={styles["metric"]}>
        <span>Passageiros com notificações</span>
        <strong>
          {summary.notifiedPassengers.toString().padStart(2, "0")}
          <small>/ {summary.totalPassengers}</small>
        </strong>
        <div className={styles["progress"]}>
          <div
            style={{
              width: `${summary.totalPassengers ? (summary.notifiedPassengers / summary.totalPassengers) * 100 : 0}%`,
            }}
          />
        </div>
      </div>
      <div className={styles["metric"]}>
        <span>Viagens com atividade</span>
        <strong>
          {summary.activeTrips.toString().padStart(2, "0")}
          <small>/ {summary.totalTrips}</small>
        </strong>
        <small>Chegadas e movimentações registradas</small>
      </div>
      <div className={styles["metric"]}>
        <span>Embarques em andamento</span>
        <strong>{summary.openBoardings.toString().padStart(2, "0")}</strong>
        <small>Viagens com embarque aberto</small>
      </div>
    </section>
  );
}
