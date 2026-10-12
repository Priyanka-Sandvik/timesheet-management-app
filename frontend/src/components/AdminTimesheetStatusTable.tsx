import { useMemo, useState } from "react";
import type { EmployeeWeekStatus, TimesheetStatus } from "@/types";
import { StatusDropdown } from "./StatusDropdown";
import styles from "./AdminTaskTable.module.css";

interface AdminTimesheetStatusTableProps {
  weeks: EmployeeWeekStatus[];
  onStatusChange: (userId: string, weekStart: string, next: TimesheetStatus) => void;
  pendingKey: string | null; // `${userId}_${weekStart}` currently being saved, or null
}

export function AdminTimesheetStatusTable({ weeks, onStatusChange, pendingKey }: AdminTimesheetStatusTableProps) {
  const [search, setSearch] = useState("");

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return weeks;
    return weeks.filter((w) => w.userId.toLowerCase().includes(q));
  }, [weeks, search]);

  return (
    <div>
      <div className={styles.filterRow}>
        <input
          className={styles.searchInput}
          placeholder="Search by employee email"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <table className={styles.table}>
        <thead>
          <tr>
            <th>Employee</th>
            <th>Week Start</th>
            <th>Week End</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((w) => {
            const key = `${w.userId}_${w.weekStart}`;
            return (
              <tr key={key}>
                <td>{w.userId}</td>
                <td>{w.weekStart}</td>
                <td>{w.weekEnd}</td>
                <td>
                  <StatusDropdown
                    value={w.status}
                    disabled={pendingKey === key}
                    onChange={(next) => onStatusChange(w.userId, w.weekStart, next)}
                  />
                </td>
              </tr>
            );
          })}
          {visible.length === 0 && (
            <tr>
              <td colSpan={4} style={{ textAlign: "center", color: "var(--color-text-muted)", padding: 24 }}>
                No timesheets found for this month.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
