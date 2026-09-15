import type { Task } from "@/types";
import { StatusBadge } from "./StatusBadge";
import styles from "./TaskCard.module.css";

export function TaskCard({ task }: { task: Task }) {
  const updated = new Date(task.updatedAt);
  const updatedLabel = isNaN(updated.getTime()) ? task.updatedAt : updated.toISOString().slice(0, 19).replace("T", " ");

  return (
    <div className={styles.card}>
      <div className={styles.title}>{task.taskName}</div>
      <div className={styles.metaRow}>
        <StatusBadge status={task.status} />
        <span className={styles.dot}>&bull;</span>
        <span className={styles.updated}>{updatedLabel}</span>
      </div>
      {task.description && <div className={styles.assignmentNote}>{task.description}</div>}
      <div className={styles.taskCode}>{task.taskCode}</div>
    </div>
  );
}
