import { useState } from "react";
import type { CreateTaskRequest, TaskStatus } from "@/types";
import styles from "./ModalShared.module.css";

interface AddTaskModalProps {
  onClose: () => void;
  onSave: (body: CreateTaskRequest) => Promise<void>;
}

export function AddTaskModal({ onClose, onSave }: AddTaskModalProps) {
  const [taskCode, setTaskCode] = useState("");
  const [taskName, setTaskName] = useState("");
  const [description, setDescription] = useState("");
  const [sponsor, setSponsor] = useState("");
  const [costCentre, setCostCentre] = useState("");
  const [coeResponsible, setCoeResponsible] = useState("");
  const [status, setStatus] = useState<TaskStatus>("Open");
  const [saving, setSaving] = useState(false);

  const canSave = taskCode.trim().length > 0 && taskName.trim().length > 0 && !saving;

  async function handleSave() {
    if (!canSave) return;
    setSaving(true);
    try {
      await onSave({
        taskCode: taskCode.trim(),
        taskName: taskName.trim(),
        description,
        sponsor,
        costCentre,
        coeResponsible,
        status,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.dialog}>
        <h3 className={styles.title}>Add Task</h3>
        <div className={styles.row2}>
          <div className={styles.field}>
            <label className={styles.label}>Task Name *</label>
            <input className={styles.input} value={taskName} onChange={(e) => setTaskName(e.target.value)} />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Task Code *</label>
            <input className={styles.input} value={taskCode} onChange={(e) => setTaskCode(e.target.value)} />
          </div>
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
          <button className={styles.confirmBtn} onClick={handleSave} disabled={!canSave}>
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
