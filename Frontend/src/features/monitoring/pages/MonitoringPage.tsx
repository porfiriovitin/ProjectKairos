import { CameraCard } from "../components/CameraCard";
import { TripList } from "../components/TripList";
import type { FrameStore } from "../model/frameStore";
import type { TravelItem } from "../model/selectors";
import styles from "./MonitoringPage.module.css";
import common from "@/shared/ui/Panel.module.css";
import { cn } from "@/shared/lib/cn";

export function MonitoringPage({
  travels,
  filter,
  frameStore,
  onSelectDestination,
}: {
  travels: TravelItem[];
  filter: string;
  frameStore: FrameStore;
  onSelectDestination: (destination: string) => void;
}) {
  return (
    <>
      <div className={common["section-heading"]}>
        <h2>Câmeras do terminal</h2>
      </div>
      <div className={styles["camera-grid"]}>
        {(["arrival", "boarding"] as const)
          .filter(
            (scene) =>
              filter === "all" ||
              (filter === "60" ? scene === "arrival" : scene === "boarding"),
          )
          .map((scene) => (
            <CameraCard key={scene} scene={scene} frameStore={frameStore} />
          ))}
      </div>
      <div className={cn(common["section-heading"], common["trips-heading"])}>
        <h2>Viagens em acompanhamento</h2>
        <span>{travels.length} viagens</span>
      </div>
      <TripList travels={travels} onSelectDestination={onSelectDestination} />
    </>
  );
}
