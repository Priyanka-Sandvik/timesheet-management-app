import { useMemo, useState } from "react";
import { taskApi } from "@/api/taskApi";
import type { Task } from "@/types";
import { TaskCard } from "./TaskCard";
import { AddProjectModal } from "./AddProjectModal";
import { useToast } from "./ToastContext";
import styles from "./TaskSidebarPanel.module.css";

interface TaskSidebarPanelProps {
  tasks: Task[];
  onProjectAdded: () => void;
}

export function TaskSidebarPanel({ tasks, onProjectAdded }: TaskSidebarPanelProps) {
  const [search, setSearch] = useState("");
  const [showAddProject, setShowAddProject] = useState(false);
  const [removingCode, setRemovingCode] = useState<string | null>(null);
  const { showToast } = useToast();

  const visibleTasks = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return tasks;
    return tasks.filter(
      (t) => t.taskName.toLowerCase().includes(q) || t.taskCode.toLowerCase().includes(q)
    );
  }, [tasks, search]);

  const hasAnyAssignment = tasks.length > 0;

  async function handleRemove(taskCode: string) {
    setRemovingCode(taskCode);
    try {
      await taskApi.unassignSelf(taskCode);
      onProjectAdded();
    } catch {
      showToast("Failed to remove project.");
    } finally {
      setRemovingCode(null);
    }
  }

  return (
    <div className={styles.panel}>
      <div className={styles.tabs}>
        <span className={`${styles.tab} ${styles.tabActive}`}>Projects</span>
      </div>

      <button className={styles.addProjectBtn} onClick={() => setShowAddProject(true)}>
        + Add Project
      </button>

      {!hasAnyAssignment ? (
        <div className={styles.emptyState}>No task assignments found</div>
      ) : (
        <>
          <div className={styles.searchRow}>
            <input
              className={styles.search}
              type="text"
              placeholder="Search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <span className={styles.searchIcon}>&#128269;</span>
          </div>

          <div className={styles.countRow}>
            <span className={styles.countLabel}>All Projects ({visibleTasks.length})</span>
          </div>

          <div className={styles.list}>
            {visibleTasks.map((task) => (
              <TaskCard
                key={task.taskCode}
                task={task}
                onRemove={handleRemove}
                removing={removingCode === task.taskCode}
              />
            ))}
          </div>
        </>
      )}

      {showAddProject && (
        <AddProjectModal
          onClose={() => setShowAddProject(false)}
          onAssigned={onProjectAdded}
        />
      )}
    </div>
  );
}
