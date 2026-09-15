import { useState } from "react";
import type { Task, TaskStatus, UpdateTaskRequest } from "@/types";
import styles from "./ModalShared.module.css";

interface EditTaskModalProps {
  task: Task;
  onClose: () => void;
  onSave: (taskCode: string, body: UpdateTaskRequest) => Promise<void>;
}

export function EditTaskModal({ task, onClose, onSave }: EditTaskModalProps) {
  const [taskName, setTaskName] = useState(task.taskName);
  const [description, setDescription] = useState(task.description ?? "");
  const [sponsor, setSponsor] = useState(task.sponsor ?? "");
  const [costCentre, setCostCentre] = useState(task.costCentre ?? "");
  const [coeResponsible, setCoeResponsible] = useState(task.coeResponsible ?? "");
  const [status, setStatus] = useState<TaskStatus>(task.status);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    setSaving(true);
    try {
      await onSave(task.taskCode, { taskName, description, sponsor, costCentre, coeResponsible, status });
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.dialog}>
        <h3 className={styles.title}>Edit Task</h3>
        <div className={styles.field}>
          <label className={styles.label}>Task Name</label>
          <input className={styles.input} value={taskName} onChange={(e) => setTaskName(e.target.value)} />
        </div>
        <div className={styles.field}>
          <label className={styles.label}>Description</label>
          <input className={styles.input} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className={styles.row2}>
          <div className={styles.field}>
            <label className={styles.label}>Sponsor</label>
            <input className={styles.input} value={sponsor} onChange={(e) => setSponsor(e.target.value)} />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Cost Centre</label>
            <input className={styles.input} value={costCentre} onChange={(e) => setCostCentre(e.target.value)} />
          </div>
        </div>
        <div className={styles.row2}>
          <div className={styles.field}>
            <label className={styles.label}>CoE Responsible</label>
            <input
              className={styles.input}
              value={coeResponsible}
              onChange={(e) => setCoeResponsible(e.target.value)}
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Status</label>
            <select className={styles.input} value={status} onChange={(e) => setStatus(e.target.value as TaskStatus)}>
              <option value="Open">Open</option>
              <option value="OnHold">On Hold</option>
              <option value="Closed">Closed</option>
            </select>
          </div>
        </div>
        <div className={styles.actions}>
          <button className={styles.cancelBtn} onClick={onClose}>
            Cancel
          </button>
          <button className={styles.confirmBtn} onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
