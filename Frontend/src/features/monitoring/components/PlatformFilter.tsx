import styles from "./PlatformFilter.module.css";

export function PlatformFilter({
  filter,
  date,
  onFilter,
}: {
  filter: string;
  date: string;
  onFilter: (filter: string) => void;
}) {
  return (
    <div className={styles["section-toolbar"]}>
      <div className={styles["tabs"]} aria-label="Filtrar por plataforma">
        {(
          [
            ["all", "Todas"],
            ["60", "Plataforma 60"],
            ["62", "Plataforma 62"],
            ["63", "Plataforma 63"],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            className={filter === value ? styles.selected : undefined}
            onClick={() => onFilter(value)}
          >
            {label}
          </button>
        ))}
      </div>
      <span className={styles["date-label"]}>{date || "Sem programação"}</span>
    </div>
  );
}
