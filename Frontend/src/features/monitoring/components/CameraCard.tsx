import { useCallback, useSyncExternalStore } from "react";
import { Icon } from "@/shared/ui/Icon";
import type { Frame } from "../model/types";
import type { FrameStore } from "../model/frameStore";
import styles from "./CameraCard.module.css";

export function CameraCard({
  scene,
  frameStore,
}: {
  scene: Frame["scene"];
  frameStore: FrameStore;
}) {
  const subscribe = useCallback(
    (listener: () => void) => frameStore.subscribe(scene, listener),
    [scene, frameStore],
  );
  const frame = useSyncExternalStore(subscribe, () => frameStore.get(scene));
  return (
    <article className={styles["camera-card"]}>
      <div className={styles["camera-top"]}>
        <span>
          <Icon name="camera" size={15} />
          {scene === "arrival" ? "Acesso ao terminal" : "Área de embarque"}
        </span>
      </div>
      {frame ? (
        <img
          data-testid="monitoring-image"
          src={frame.image}
          alt={
            scene === "arrival"
              ? "Área de chegada ao terminal"
              : "Plataformas de embarque"
          }
        />
      ) : (
        <div data-testid="camera-empty" className={styles["camera-empty"]}>
          <Icon name="camera" size={36} />
          <strong>Aguardando transmissão</strong>
          <span>A imagem será exibida quando estiver disponível.</span>
        </div>
      )}
      <div className={styles["camera-caption"]}>
        <div>
          <span>CÂMERA {scene === "arrival" ? "01" : "02"}</span>
          <strong>
            {scene === "arrival"
              ? "Chegada ao terminal"
              : "Plataformas 62 e 63"}
          </strong>
        </div>
      </div>
    </article>
  );
}
