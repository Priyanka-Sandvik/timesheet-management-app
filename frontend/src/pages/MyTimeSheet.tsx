import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/auth/AuthContext";
import { taskApi } from "@/api/taskApi";
import { timelogApi } from "@/api/timelogApi";
import type { Task, TimesheetResponse } from "@/types";
import { getWeekDays, getWeekStart, isFutureWeek, toIsoDate } from "@/utils/date";
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

  // Called after the employee adds a project from the sidebar. If this week's cards were
  // already generated (and the week isn't locked), pull the new task onto the sheet too;
  // otherwise it would only show up on weeks generated later.
  async function handleProjectAdded() {
    await loadTasks();
    if (hasLoggedCards && !readOnly) {
      await handleGenerate();
    }
  }

  // Adds one assigned task back onto the viewed week at 0h (all 7 days), e.g. after its
  // card was removed from this week.
  async function handleAddTaskToWeek(taskCode: string) {
    try {
      await timelogApi.bulkUpsertEntries({
        weekStart: weekStartIso,
        entries: weekDays.map((d) => ({ taskCode, entryDate: toIsoDate(d), hours: 0 })),
      });
      await loadTimesheet();
    } catch (err) {
      console.error(err);
      showToast("Failed to add task to this week.");
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
    // Week-scoped: deletes this task's rows for the viewed week only. The assignment and
    // every other week stay as they are.
    try {
      await timelogApi.removeTaskFromWeek(weekStartIso, taskCode);
      await loadTimesheet();
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

  // Rows exist as soon as the week is generated (initially at 0 hours each) — this must
  // not require any hours to already be entered, or the grid never leaves the empty state
  // after "Generate Time Cards".
  const hasLoggedCards = (timesheet?.entries.length ?? 0) > 0;

  // Assigned tasks with no row on this week's sheet - e.g. assigned by an admin after the
  // week was generated. Re-generating only adds the missing rows (at 0h) and leaves
  // everything already on the sheet untouched.
  const missingTaskCodes = useMemo(() => {
    const onSheet = new Set(timesheet?.entries.map((e) => e.taskCode) ?? []);
    // Closed tasks are never added to a time sheet, so they aren't offered either.
    return new Set(
      tasks.filter((t) => t.status !== "Closed" && !onSheet.has(t.taskCode)).map((t) => t.taskCode)
    );
  }, [tasks, timesheet]);
  const missingTaskCount = missingTaskCodes.size;

  // Sidebar "+" is offered only on a generated, editable week (an empty week uses Generate).
  const addableTaskCodes = useMemo(
    () => (hasLoggedCards && !readOnly ? missingTaskCodes : new Set<string>()),
    [hasLoggedCards, readOnly, missingTaskCodes]
  );

  // Employees can't submit a week that starts in a future month — the current month's
  // broken last week (Monday this month, Sunday spilling into next) is still fine. Admins
  // are exempt, same as the read-only lock on submitted weeks.
  const isFuturePeriod = !isAdmin && isFutureWeek(weekStart);

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
          disabled={submitting || readOnly || !hasLoggedCards || isFuturePeriod}
          title={isFuturePeriod ? "This week hasn't started yet and cannot be submitted." : undefined}
        >
          {submitting ? "Submitting..." : "Submit"}
        </button>
      </div>

      <div className={styles.body}>
        <TaskSidebarPanel
          tasks={tasks}
          addableTaskCodes={addableTaskCodes}
          onProjectAdded={handleProjectAdded}
          onAddToWeek={handleAddTaskToWeek}
        />

        <div className={styles.main}>
          {!loading && timesheet && (
            <>
              <TimesheetGrid
                weekDays={weekDays}
                dailyTotals={timesheet.dailyTotals}
                weeklyTotal={timesheet.weeklyTotal}
                entries={timesheet.entries}
              />

              <div className={styles.loggedTitleRow}>
                <div className={styles.loggedTitle}>Logged Time Cards</div>
                {hasLoggedCards && !readOnly && missingTaskCount > 0 && (
                  <button className={styles.syncBtn} onClick={handleGenerate} disabled={busy}>
                    {busy
                      ? "Adding..."
                      : `Add ${missingTaskCount} new ${missingTaskCount === 1 ? "task" : "tasks"} to this week`}
                  </button>
                )}
              </div>

              {hasLoggedCards ? (
                <LoggedTimeCardsTable
                  entries={timesheet.entries}
                  weekDays={weekDays}
                  readOnly={readOnly}
                  onHourChange={handleHourChange}
                  onRemoveTask={handleRemoveTask}
                />
              ) : (
                <EmptyStateActions onGenerate={handleGenerate} busy={busy} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
