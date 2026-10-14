import { useState } from "react";
import { SideNavigation } from "./components/SideNavigation";
import { pages } from "./navigation";
import type { PageId } from "./navigation";
import { PageHeading } from "@/shared/ui/PageHeading";
import {
  useMonitoring,
  useMonitoringView,
  OperationSummary,
  PlatformFilter,
  NotificationFeed,
  NotificationDetails,
  MonitoringPage,
  PassengersPage,
  NotificationsPage,
  exportMonitoringReport,
} from "@/features/monitoring";
import styles from "./App.module.css";

export default function App() {
  const { data, error, frameStore } = useMonitoring();
  const view = useMonitoringView(data);
  const [page, setPage] = useState<PageId>("overview");
  const [notice, setNotice] = useState("");
  async function fullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch {
      setNotice("O navegador não permitiu abrir a tela cheia.");
    }
  }
  function selectDestination(destination: string) {
    view.setSearch(destination);
    setPage("passengers");
  }

  return (
    <div className={styles["app-shell"]}>
      <SideNavigation
        page={page}
        onNavigate={setPage}
        onFullscreen={fullscreen}
      />
      <div className={styles.workspace}>
        <main className={styles.main}>
          <PageHeading
            {...pages[page]}
            canExport={Boolean(data.session_id)}
            onExport={() => exportMonitoringReport(data, view.summary)}
          />
          {error && (
            <p className={styles["operation-notice"]} role="status">
              {data.session_id
                ? "Atualizações temporariamente indisponíveis. Exibindo os últimos registros recebidos."
                : "Aguardando disponibilidade do monitoramento."}
            </p>
          )}
          {notice && (
            <p className={styles["operation-notice"]} role="status">
              {notice}
            </p>
          )}
          <OperationSummary summary={view.summary} />
          <div className={styles["content-layout"]}>
            <div className={styles["main-column"]}>
              <PlatformFilter
                date={data.date}
                filter={view.filter}
                onFilter={view.setFilter}
              />
              {page === "overview" && (
                <MonitoringPage
                  travels={view.travels}
                  filter={view.filter}
                  frameStore={frameStore}
                  onSelectDestination={selectDestination}
                />
              )}
              {page === "passengers" && (
                <PassengersPage
                  passengers={view.passengers}
                  search={view.search}
                  passengerFilter={view.passengerFilter}
                  onSearch={view.setSearch}
                  onStatusFilter={view.setPassengerFilter}
                  onSelect={view.selectNotification}
                />
              )}
              {page === "events" && (
                <NotificationsPage
                  events={view.events}
                  onSelect={view.selectNotification}
                />
              )}
            </div>
            <NotificationFeed
              date={data.date}
              notifications={view.notifications}
              onSelect={view.selectNotification}
            />
          </div>
        </main>
      </div>
      <NotificationDetails
        notification={view.details}
        onClose={view.closeNotification}
      />
    </div>
  );
}
