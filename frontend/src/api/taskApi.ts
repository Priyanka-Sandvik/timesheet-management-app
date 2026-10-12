import { apiClient } from "./client";
import type {
  AssignTasksRequest,
  AssignTasksResponse,
  CreateTaskRequest,
  TaskImportResponse,
  TasksListResponse,
  UpdateTaskRequest,
  Task,
} from "@/types";

export const taskApi = {
  /** Employee-scoped read. Never used to write to the Tasks table. */
  listMine(params?: { search?: string }) {
    return apiClient.request<TasksListResponse>("task", "/api/v1/tasks", {
      query: { scope: "mine", search: params?.search },
    });
  },

  /** Open task templates the caller can self-assign to (excludes ones already assigned). */
  listCatalog(params?: { search?: string }) {
    return apiClient.request<TasksListResponse>("task", "/api/v1/tasks/catalog", {
      query: { search: params?.search },
    });
  },

  /** Employee self-assignment to an existing Open task - never creates new tasks. */
  assignSelf(taskCode: string) {
    return apiClient.request<Task>("task", `/api/v1/tasks/${encodeURIComponent(taskCode)}/assign-self`, {
      method: "POST",
    });
  },

  /** Employee self-removal from a task they're assigned to. */
  unassignSelf(taskCode: string) {
    return apiClient.request<void>("task", `/api/v1/tasks/${encodeURIComponent(taskCode)}/assign-self`, {
      method: "DELETE",
    });
  },

  // --- Admin-only surfaces (Task Import / Task Management screens only) ---

  adminImport(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.request<TaskImportResponse>("task", "/admin/tasks/import", {
      method: "POST",
      body: formData,
      isFormData: true,
    });
  },

  adminCreate(body: CreateTaskRequest) {
    return apiClient.request<Task>("task", "/admin/tasks", {
      method: "POST",
      body,
    });
  },

  adminList(params?: { page?: string; search?: string; status?: string }) {
    return apiClient.request<TasksListResponse>("task", "/admin/tasks", {
      query: {
        continuationToken: params?.page,
        search: params?.search,
        status: params?.status,
      },
    });
  },

  adminAssign(taskCode: string, body: AssignTasksRequest) {
    return apiClient.request<AssignTasksResponse>("task", `/admin/tasks/${encodeURIComponent(taskCode)}/assign`, {
      method: "POST",
      body,
    });
  },

  adminUnassign(taskCode: string, email: string) {
    return apiClient.request<void>(
      "task",
      `/admin/tasks/${encodeURIComponent(taskCode)}/assign/${encodeURIComponent(email)}`,
      { method: "DELETE" }
    );
  },

  adminUpdate(taskCode: string, body: UpdateTaskRequest) {
    return apiClient.request<Task>("task", `/admin/tasks/${encodeURIComponent(taskCode)}`, {
      method: "PUT",
      body,
    });
  },

  adminDeactivate(taskCode: string) {
    return apiClient.request<void>("task", `/admin/tasks/${encodeURIComponent(taskCode)}`, {
      method: "DELETE",
    });
  },
};
