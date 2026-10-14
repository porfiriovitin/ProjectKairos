import { Icon } from "./Icon";
import styles from "./PageHeading.module.css";

export function PageHeading({
  title,
  description,
  canExport,
  onExport,
}: {
  title: string;
  description: string;
  canExport: boolean;
  onExport: () => void;
}) {
  return (
    <section className={styles["page-heading"]}>
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <button
        className={styles["secondary-button"]}
        aria-label="Exportar relatório"
        onClick={onExport}
        disabled={!canExport}
      >
        <Icon name="download" size={16} />
        Exportar relatório
      </button>
    </section>
  );
}
