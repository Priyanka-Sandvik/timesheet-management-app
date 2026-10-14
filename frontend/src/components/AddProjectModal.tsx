import { useEffect, useMemo, useState } from "react";
import { taskApi } from "@/api/taskApi";
import type { Task } from "@/types";
import styles from "./ModalShared.module.css";

interface AddProjectModalProps {
  onClose: () => void;
  onAssigned: () => void;
}

export function AddProjectModal({ onClose, onAssigned }: AddProjectModalProps) {
  const [search, setSearch] = useState("");
  const [catalog, setCatalog] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assigningCode, setAssigningCode] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    taskApi
      .listCatalog()
      .then((res) => {
        if (!cancelled) setCatalog(res.tasks);
      })
      .catch(() => {
        if (!cancelled) setError("Unable to load available projects.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return catalog;
    return catalog.filter(
      (t) => t.taskName.toLowerCase().includes(q) || t.taskCode.toLowerCase().includes(q)
    );
  }, [catalog, search]);

  async function handleAssign(taskCode: string) {
    setAssigningCode(taskCode);
    setError(null);
    try {
      await taskApi.assignSelf(taskCode);
      setCatalog((prev) => prev.filter((t) => t.taskCode !== taskCode));
      onAssigned();
    } catch {
      setError("Failed to add this project. Please try again.");
    } finally {
      setAssigningCode(null);
    }
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.dialog}>
        <h3 className={styles.title}>Add Project</h3>

        <div className={styles.field}>
          <label className={styles.label}>Available Projects</label>
          <input
            className={styles.input}
            placeholder="Search by task name or code"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {error && <div style={{ color: "var(--color-danger)", fontSize: 13, marginBottom: 10 }}>{error}</div>}

        <div className={styles.pickList}>
          {loading && <div className={styles.pickItem}>Loading...</div>}
          {!loading &&
            visible.map((task) => (
              <div key={task.taskCode} className={styles.pickItem} style={{ justifyContent: "space-between" }}>
                <span>
                  {task.taskName} ({task.taskCode})
                </span>
                <button
                  className={styles.confirmBtn}
                  onClick={() => handleAssign(task.taskCode)}
                  disabled={assigningCode === task.taskCode}
                >
                  {assigningCode === task.taskCode ? "Adding..." : "Add"}
                </button>
              </div>
            ))}
          {!loading && visible.length === 0 && (
            <div className={styles.pickItem} style={{ color: "var(--color-text-muted)" }}>
              No available projects found.
            </div>
          )}
        </div>

        <div className={styles.actions}>
          <button className={styles.cancelBtn} onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
