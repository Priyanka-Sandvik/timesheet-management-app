import type { Task } from "@/types";
import { StatusBadge } from "./StatusBadge";
import styles from "./TaskCard.module.css";

interface TaskCardProps {
  task: Task;
  onRemove?: (taskCode: string) => void;
  removing?: boolean;
}

export function TaskCard({ task, onRemove, removing }: TaskCardProps) {
  const updated = new Date(task.updatedAt);
  const updatedLabel = isNaN(updated.getTime()) ? task.updatedAt : updated.toISOString().slice(0, 19).replace("T", " ");

  return (
    <div className={styles.card}>
      <div className={styles.headerRow}>
        <div className={styles.title}>{task.taskName}</div>
        {onRemove && (
          <button
            className={styles.removeBtn}
            onClick={() => onRemove(task.taskCode)}
            disabled={removing}
            aria-label={`Remove ${task.taskName} from your projects`}
            title="Remove from my projects"
          >
            {removing ? "..." : "×"}
          </button>
        )}
      </div>
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
