import styles from "./EmptyStateActions.module.css";

interface EmptyStateActionsProps {
  onGenerate: () => void;
  busy?: boolean;
}

export function EmptyStateActions({ onGenerate, busy }: EmptyStateActionsProps) {
  return (
    <div className={styles.wrapper}>
      <p className={styles.message}>No Time Cards logged yet.</p>
      <button className={styles.primaryBtn} onClick={onGenerate} disabled={busy}>
        Generate Time Cards
      </button>
    </div>
  );
}
