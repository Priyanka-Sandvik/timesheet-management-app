import type { Task } from "@/types";
import { StatusBadge } from "./StatusBadge";
import styles from "./AdminTaskTable.module.css";

interface AdminTaskTableProps {
  tasks: Task[]; // template rows only (one per taskCode)
  assignedCounts: Record<string, number>;
  search: string;
  onSearchChange: (v: string) => void;
  statusFilter: string;
  onStatusFilterChange: (v: string) => void;
  onEdit: (task: Task) => void;
  onAssign: (task: Task) => void;
  onDeactivate: (task: Task) => void;
  hasNextPage: boolean;
  hasPrevPage: boolean;
  onNextPage: () => void;
  onPrevPage: () => void;
}

export function AdminTaskTable({
  tasks,
  assignedCounts,
  search,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  onEdit,
  onAssign,
  onDeactivate,
  hasNextPage,
  hasPrevPage,
  onNextPage,
  onPrevPage,
}: AdminTaskTableProps) {
  return (
    <div>
      <div className={styles.filterRow}>
        <input
          className={styles.searchInput}
          placeholder="Search by TaskCode or TaskName"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
        />
        <select className={styles.select} value={statusFilter} onChange={(e) => onStatusFilterChange(e.target.value)}>
          <option value="">All Statuses</option>
          <option value="Open">Open</option>
          <option value="OnHold">On Hold</option>
          <option value="Closed">Closed</option>
        </select>
      </div>

      <table className={styles.table}>
        <thead>
          <tr>
            <th>Task Name</th>
            <th>Task Code</th>
            <th>Description</th>
            <th>Sponsor</th>
            <th>Cost Centre</th>
            <th>CoE Responsible</th>
            <th>Status</th>
            <th>Assigned Count</th>
            <th>Last Updated</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr key={task.taskCode}>
              <td>{task.taskName}</td>
              <td>{task.taskCode}</td>
              <td>{task.description ?? "-"}</td>
              <td>{task.sponsor ?? "-"}</td>
              <td>{task.costCentre ?? "-"}</td>
              <td>{task.coeResponsible ?? "-"}</td>
              <td>
                <StatusBadge status={task.status} />
              </td>
              <td>{assignedCounts[task.taskCode] ?? 0}</td>
              <td>{new Date(task.updatedAt).toLocaleDateString()}</td>
              <td>
                <div className={styles.actionsCell}>
                  <button className={styles.actionBtn} onClick={() => onEdit(task)}>
                    Edit
                  </button>
                  <button className={styles.actionBtn} onClick={() => onAssign(task)}>
                    Assign
                  </button>
                  <button className={styles.dangerActionBtn} onClick={() => onDeactivate(task)}>
                    Deactivate
                  </button>
                </div>
              </td>
            </tr>
          ))}
          {tasks.length === 0 && (
            <tr>
              <td colSpan={10} style={{ textAlign: "center", color: "var(--color-text-muted)", padding: 24 }}>
                No tasks found.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <div className={styles.pagination}>
        <button className={styles.pageBtn} disabled={!hasPrevPage} onClick={onPrevPage}>
          Previous
        </button>
        <button className={styles.pageBtn} disabled={!hasNextPage} onClick={onNextPage}>
          Next
        </button>
      </div>
    </div>
  );
}
