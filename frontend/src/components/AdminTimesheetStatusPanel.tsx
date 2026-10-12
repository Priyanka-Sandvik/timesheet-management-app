import { useEffect, useState } from "react";
import { timelogApi } from "@/api/timelogApi";
import { getPreviousMonthValue } from "@/utils/date";
import type { EmployeeWeekStatus, TimesheetStatus } from "@/types";
import { useToast } from "./ToastContext";
import { AdminTimesheetStatusTable } from "./AdminTimesheetStatusTable";
import styles from "./MonthlyExportPanel.module.css";

export function AdminTimesheetStatusPanel() {
  const [month, setMonth] = useState(getPreviousMonthValue());
  const [weeks, setWeeks] = useState<EmployeeWeekStatus[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const { showToast } = useToast();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    timelogApi
      .getAdminPeriodStatuses(month)
      .then((res) => {
        if (!cancelled) setWeeks(res.employees);
      })
      .catch(() => {
        if (!cancelled) setError("Unable to load timesheet statuses for this month.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [month]);

  async function handleStatusChange(userId: string, weekStart: string, next: TimesheetStatus) {
    const key = `${userId}_${weekStart}`;
    setPendingKey(key);
    try {
      await timelogApi.setAdminWeekStatus(userId, weekStart, next);
      setWeeks((prev) => prev.map((w) => (w.userId === userId && w.weekStart === weekStart ? { ...w, status: next } : w)));
    } catch {
      showToast(`Failed to update status for ${userId}`, "error");
    } finally {
      setPendingKey(null);
    }
  }

  return (
    <div>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="status-review-month">
          Month
        </label>
        <input
          id="status-review-month"
          type="month"
          className={styles.input}
          value={month}
          onChange={(e) => setMonth(e.target.value)}
        />
      </div>

      {error && <div className={styles.errorBox}>{error}</div>}
      {loading ? (
        <p>Loading...</p>
      ) : (
        <AdminTimesheetStatusTable weeks={weeks} onStatusChange={handleStatusChange} pendingKey={pendingKey} />
      )}
    </div>
  );
}
