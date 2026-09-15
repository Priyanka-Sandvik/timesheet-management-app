import styles from "./EmptyStateActions.module.css";

interface EmptyStateActionsProps {
  onGenerate: () => void;
  onCopyPrevious: () => void;
  busy?: boolean;
}

export function EmptyStateActions({ onGenerate, onCopyPrevious, busy }: EmptyStateActionsProps) {
  return (
    <div className={styles.wrapper}>
      <p className={styles.message}>No Time Cards logged yet.</p>
      <button className={styles.primaryBtn} onClick={onGenerate} disabled={busy}>
        Generate Time Cards
      </button>
      <button className={styles.secondaryBtn} onClick={onCopyPrevious} disabled={busy}>
        Copy from previous Time Sheet
      </button>
    </div>
  );
}
