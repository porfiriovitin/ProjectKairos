import { Icon } from "@/shared/ui/Icon";
import type { PageId } from "../navigation";
import styles from "./SideNavigation.module.css";
import { cn } from "@/shared/lib/cn";

export function SideNavigation({
  page,
  onNavigate,
  onFullscreen,
}: {
  page: PageId;
  onNavigate: (page: PageId) => void;
  onFullscreen: () => void;
}) {
  return (
    <aside className={styles["sidebar"]}>
      <a
        className={styles["brand"]}
        href="#"
        aria-label="Kairos — início"
        onClick={(event) => {
          event.preventDefault();
          onNavigate("overview");
        }}
      >
        k<span className={styles["brand-dot"]}>.</span>
      </a>
      <nav aria-label="Navegação principal">
        {(
          [
            ["overview", "grid", "Monitoramento"],
            ["passengers", "people", "Passageiros"],
            ["events", "bell", "Notificações"],
          ] as const
        ).map(([id, icon, label]) => (
          <button
            key={id}
            title={label}
            aria-label={label}
            aria-current={page === id ? "page" : undefined}
            className={cn(styles["nav-button"], page === id && styles.active)}
            onClick={() => onNavigate(id)}
          >
            <Icon name={icon} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className={styles["sidebar-bottom"]}>
        <button
          className={styles["nav-button"]}
          aria-label="Alternar tela cheia"
          title="Tela cheia"
          onClick={onFullscreen}
        >
          <Icon name="expand" />
        </button>
      </div>
    </aside>
  );
}
