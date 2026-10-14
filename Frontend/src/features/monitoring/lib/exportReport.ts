import { downloadJson } from "../../../shared/lib/downloadJson";
import type { Snapshot } from "../model/types";
import type { OperationSummaryModel } from "../model/selectors";

export function exportMonitoringReport(
  data: Snapshot,
  summary: OperationSummaryModel,
) {
  downloadJson(
    {
      ...data,
      frames: undefined,
      notification_count: summary.notifications,
      notified_passengers: [
        ...new Set(data.events.flatMap((event) => event.passenger_codes)),
      ],
    },
    `kairos-relatorio-${data.date.replaceAll("/", "-") || "sem-dados"}.json`,
  );
}
