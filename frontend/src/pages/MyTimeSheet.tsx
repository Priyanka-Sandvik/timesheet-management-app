import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/auth/AuthContext";
import { taskApi } from "@/api/taskApi";
import { timelogApi } from "@/api/timelogApi";
import type { Task, TimesheetResponse } from "@/types";
import { getWeekDays, getWeekStart, toIsoDate } from "@/utils/date";
import { WeekNavigator } from "@/components/WeekNavigator";
import { StatusBadge } from "@/components/StatusBadge";
import { TaskSidebarPanel } from "@/components/TaskSidebarPanel";
import { TimesheetGrid } from "@/components/TimesheetGrid";
import { LoggedTimeCardsTable } from "@/components/LoggedTimeCardsTable";
import { EmptyStateActions } from "@/components/EmptyStateActions";
import { useToast } from "@/components/ToastContext";
import styles from "./MyTimeSheet.module.css";

function getInitials(name: string | null, email: string | undefined): string {
  if (name) {
    return name.trim().split(/\s+/).slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("");
  }
  return email?.[0]?.toUpperCase() ?? "?";
}

export function MyTimeSheet() {
  const { claims, isAdmin, fullName } = useAuth();
  const { showToast } = useToast();
  const userId = claims?.sub as string | undefined;

  const [weekStart, setWeekStart] = useState<Date>(() => getWeekStart(new Date()));
  const [tasks, setTasks] = useState<Task[]>([]);
  const [timesheet, setTimesheet] = useState<TimesheetResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  // Client-side only: the backend has no delete-entries route, so "removing" a task
  // zeroes its hours (see LoggedTimeCardsTable) and we hide the row locally. Reset
  // whenever the viewed week changes.
  const [removedTaskCodes, setRemovedTaskCodes] = useState<Set<string>>(new Set());

  const weekStartIso = useMemo(() => toIsoDate(weekStart), [weekStart]);
  const weekDays = useMemo(() => getWeekDays(weekStart), [weekStart]);

  const loadTimesheet = useCallback(async () => {
    if (!userId) return;
    try {
      const data = await timelogApi.getWeek(userId, weekStartIso);
      setTimesheet(data);
    } catch (err) {
      console.error(err);
      showToast("Failed to load time sheet.");
    }
  }, [userId, weekStartIso, showToast]);

  const loadTasks = useCallback(async () => {
    try {
      const data = await taskApi.listMine();
      setTasks(data.tasks);
    } catch (err) {
      console.error(err);
      showToast("Failed to load assigned tasks.");
    }
  }, [showToast]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  useEffect(() => {
    setLoading(true);
    loadTimesheet().finally(() => setLoading(false));
  }, [loadTimesheet]);

  useEffect(() => {
    setRemovedTaskCodes(new Set());
  }, [weekStartIso]);

  const isSubmitted = timesheet?.status === "Submitted";
  const readOnly = isSubmitted && !isAdmin;

  async function handleGenerate() {
    setBusy(true);
    try {
      await timelogApi.generate(weekStartIso);
      await loadTimesheet();
    } catch (err) {
      console.error(err);
      showToast("Failed to generate time cards.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCopyPrevious() {
    setBusy(true);
    try {
      await timelogApi.copyPrevious(weekStartIso);
      await loadTimesheet();
    } catch (err) {
      console.error(err);
      showToast("Failed to copy from previous time sheet.");
    } finally {
      setBusy(false);
    }
  }

  async function handleHourChange(taskCode: string, entryDate: string, hours: number) {
    try {
      await timelogApi.bulkUpsertEntries({
        weekStart: weekStartIso,
        entries: [{ taskCode, entryDate, hours }],
      });
      await loadTimesheet();
    } catch (err) {
      console.error(err);
      showToast("Failed to save hours.");
    }
  }

  async function handleRemoveTask(taskCode: string) {
    // See LoggedTimeCardsTable.tsx for why this zeroes hours instead of
    // calling an undocumented delete-entries endpoint.
    try {
      await timelogApi.bulkUpsertEntries({
        weekStart: weekStartIso,
        entries: weekDays.map((d) => ({ taskCode, entryDate: toIsoDate(d), hours: 0 })),
      });
      await loadTimesheet();
      setRemovedTaskCodes((prev) => new Set(prev).add(taskCode));
    } catch (err) {
      console.error(err);
      showToast("Failed to remove task from this week.");
    }
  }

  async function handleSubmit() {
    setSubmitting(true);
    try {
      await timelogApi.submit(weekStartIso);
      await loadTimesheet();
      showToast("Time sheet submitted.", "success");
    } catch (err) {
      console.error(err);
      showToast("Failed to submit time sheet.");
    } finally {
      setSubmitting(false);
    }
  }

  // Rows exist as soon as the week is generated/copied (initially at 0 hours each) — this
  // must not require any hours to already be entered, or the grid never leaves the empty
  // state after "Generate Time Cards".
  const hasLoggedCards = (timesheet?.entries.length ?? 0) > 0;

  return (
    <div>
      <div className={styles.pageHeaderRow}>
        <div className={styles.titleBlock}>
          <span className={styles.avatar}>{getInitials(fullName, userId)}</span>
          <h1 className={styles.title}>My Time Sheet</h1>
        </div>

        <div className={styles.centerNav}>
          <WeekNavigator weekStart={weekStart} onChangeWeekStart={setWeekStart} />
          <div className={styles.statusRow}>
            <StatusBadge status={isSubmitted ? "Submitted" : "Pending"} />
          </div>
        </div>

        <button
          className={styles.submitBtn}
          onClick={handleSubmit}
          disabled={submitting || readOnly || !hasLoggedCards}
        >
          {submitting ? "Submitting..." : "Submit"}
        </button>
      </div>

      <div className={styles.body}>
        <TaskSidebarPanel tasks={tasks} />

        <div className={styles.main}>
          {!loading && timesheet && (
            <>
              <TimesheetGrid
                weekDays={weekDays}
                dailyTotals={timesheet.dailyTotals}
                weeklyTotal={timesheet.weeklyTotal}
                entries={timesheet.entries}
              />

              <div className={styles.loggedTitle}>Logged Time Cards</div>

              {hasLoggedCards ? (
                <LoggedTimeCardsTable
                  entries={timesheet.entries}
                  weekDays={weekDays}
                  readOnly={readOnly}
                  removedTaskCodes={removedTaskCodes}
                  onHourChange={handleHourChange}
                  onRemoveTask={handleRemoveTask}
                />
              ) : (
                <EmptyStateActions
                  onGenerate={handleGenerate}
                  onCopyPrevious={handleCopyPrevious}
                  busy={busy}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
