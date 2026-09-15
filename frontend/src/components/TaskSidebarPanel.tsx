import { useMemo, useState } from "react";
import type { Task } from "@/types";
import { TaskCard } from "./TaskCard";
import styles from "./TaskSidebarPanel.module.css";

export function TaskSidebarPanel({ tasks }: { tasks: Task[] }) {
  const [search, setSearch] = useState("");

  const visibleTasks = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return tasks;
    return tasks.filter(
      (t) => t.taskName.toLowerCase().includes(q) || t.taskCode.toLowerCase().includes(q)
    );
  }, [tasks, search]);

  const hasAnyAssignment = tasks.length > 0;

  return (
    <div className={styles.panel}>
      <div className={styles.tabs}>
        <span className={`${styles.tab} ${styles.tabActive}`}>Projects</span>
      </div>

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
              <TaskCard key={task.taskCode} task={task} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
