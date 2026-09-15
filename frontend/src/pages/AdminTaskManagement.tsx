import { useCallback, useEffect, useMemo, useState } from "react";
import { taskApi } from "@/api/taskApi";
import { profileApi } from "@/api/profileApi";
import type { Task, User } from "@/types";
import { AdminTaskTable } from "@/components/AdminTaskTable";
import { AddTaskModal } from "@/components/AddTaskModal";
import { EditTaskModal } from "@/components/EditTaskModal";
import { AssignEmployeesModal } from "@/components/AssignEmployeesModal";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useToast } from "@/components/ToastContext";
import styles from "./AdminTaskManagement.module.css";

const UNASSIGNED_MARKER = "UNASSIGNED";

export function AdminTaskManagement() {
  const { showToast } = useToast();
  const [allRows, setAllRows] = useState<Task[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [pageTokens, setPageTokens] = useState<(string | undefined)[]>([undefined]);
  const [pageIndex, setPageIndex] = useState(0);
  const [nextPage, setNextPage] = useState<string | null | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [assigningTask, setAssigningTask] = useState<Task | null>(null);
  const [deactivatingTask, setDeactivatingTask] = useState<Task | null>(null);
  const [addingTask, setAddingTask] = useState(false);

  const loadPage = useCallback(
    async (page: string | undefined) => {
      setLoading(true);
      try {
        const response = await taskApi.adminList({ page, search: search || undefined, status: statusFilter || undefined });
        setAllRows(response.tasks);
        setNextPage(response.nextPage ?? null);
      } catch (err) {
        console.error(err);
        showToast("Failed to load tasks.");
      } finally {
        setLoading(false);
      }
    },
    [search, statusFilter, showToast]
  );

  const loadUsers = useCallback(async () => {
    try {
      const response = await profileApi.adminListUsers();
      setUsers(response.users);
    } catch (err) {
      console.error(err);
      showToast("Failed to load employee list.");
    }
  }, [showToast]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  useEffect(() => {
    setPageTokens([undefined]);
    setPageIndex(0);
    loadPage(undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, statusFilter]);

  // Group rows by taskCode: template row (assignedUserId UNASSIGNED/absent) plus one row per assignment.
  const { templateTasks, assignedCounts, assignedEmailsByTask } = useMemo(() => {
    const templates = new Map<string, Task>();
    const counts: Record<string, number> = {};
    const emails: Record<string, string[]> = {};

    for (const row of allRows) {
      const isTemplate = !row.assignedUserId || row.assignedUserId === UNASSIGNED_MARKER;
      if (isTemplate) {
        templates.set(row.taskCode, row);
      } else {
        counts[row.taskCode] = (counts[row.taskCode] ?? 0) + 1;
        emails[row.taskCode] = [...(emails[row.taskCode] ?? []), row.assignedUserId as string];
      }
    }
    return { templateTasks: Array.from(templates.values()), assignedCounts: counts, assignedEmailsByTask: emails };
  }, [allRows]);

  function handleNextPage() {
    if (!nextPage) return;
    setPageTokens((prev) => [...prev, nextPage]);
    setPageIndex((i) => i + 1);
    loadPage(nextPage);
  }

  function handlePrevPage() {
    if (pageIndex === 0) return;
    const newIndex = pageIndex - 1;
    setPageIndex(newIndex);
    loadPage(pageTokens[newIndex]);
  }

  async function handleAddTask(body: Parameters<typeof taskApi.adminCreate>[0]) {
    try {
      await taskApi.adminCreate(body);
      showToast("Task created.", "success");
      loadPage(pageTokens[pageIndex]);
    } catch (err) {
      console.error(err);
      showToast("Failed to create task.");
      throw err;
    }
  }

  async function handleSaveEdit(taskCode: string, body: Parameters<typeof taskApi.adminUpdate>[1]) {
    try {
      await taskApi.adminUpdate(taskCode, body);
      showToast("Task updated.", "success");
      loadPage(pageTokens[pageIndex]);
    } catch (err) {
      console.error(err);
      showToast("Failed to update task.");
      throw err;
    }
  }

  async function handleAssign(taskCode: string, emails: string[]) {
    try {
      await taskApi.adminAssign(taskCode, { emails });
      showToast("Employees assigned.", "success");
      loadPage(pageTokens[pageIndex]);
    } catch (err) {
      console.error(err);
      showToast("Failed to assign employees.");
      throw err;
    }
  }

  async function handleUnassign(taskCode: string, email: string) {
    try {
      await taskApi.adminUnassign(taskCode, email);
      showToast("Employee un-assigned.", "success");
      loadPage(pageTokens[pageIndex]);
    } catch (err) {
      console.error(err);
      showToast("Failed to un-assign employee.");
      throw err;
    }
  }

  async function confirmDeactivate() {
    if (!deactivatingTask) return;
    try {
      await taskApi.adminDeactivate(deactivatingTask.taskCode);
      showToast("Task template removed.", "success");
      loadPage(pageTokens[pageIndex]);
    } catch (err) {
      console.error(err);
      showToast("Failed to deactivate task.");
    } finally {
      setDeactivatingTask(null);
    }
  }

  return (
    <div>
      <div className={styles.toolbar}>
        <button className={styles.addBtn} onClick={() => setAddingTask(true)}>
          Add Task
        </button>
      </div>

      <AdminTaskTable
        tasks={templateTasks}
        assignedCounts={assignedCounts}
        search={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onEdit={setEditingTask}
        onAssign={setAssigningTask}
        onDeactivate={setDeactivatingTask}
        hasNextPage={!!nextPage}
        hasPrevPage={pageIndex > 0}
        onNextPage={handleNextPage}
        onPrevPage={handlePrevPage}
      />

      {loading && <p style={{ color: "var(--color-text-muted)" }}>Loading...</p>}

      {addingTask && <AddTaskModal onClose={() => setAddingTask(false)} onSave={handleAddTask} />}

      {editingTask && (
        <EditTaskModal task={editingTask} onClose={() => setEditingTask(null)} onSave={handleSaveEdit} />
      )}

      {assigningTask && (
        <AssignEmployeesModal
          taskCode={assigningTask.taskCode}
          taskLabel={assigningTask.taskName}
          allUsers={users}
          assignedEmails={assignedEmailsByTask[assigningTask.taskCode] ?? []}
          onClose={() => setAssigningTask(null)}
          onAssign={handleAssign}
          onUnassign={handleUnassign}
        />
      )}

      <ConfirmDialog
        open={!!deactivatingTask}
        title="Deactivate Task"
        message="This will remove the task template. Existing employee assignments are not affected. Continue?"
        confirmLabel="Deactivate"
        danger
        onConfirm={confirmDeactivate}
        onCancel={() => setDeactivatingTask(null)}
      />
    </div>
  );
}
