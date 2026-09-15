// Matches architecture doc §6 Tasks entity and §8.2 Task Service API contracts.

export type TaskStatus = "Open" | "OnHold" | "Closed";

export interface Task {
  taskCode: string;
  taskName: string;
  description: string | null;
  sponsor: string | null;
  costCentre: string | null;
  coeResponsible: string | null;
  status: TaskStatus;
  assignedUserId?: string | null;
  assignedCount?: number;
  createdAt: string;
  updatedAt: string;
}

export interface TasksListResponse {
  tasks: Task[];
  nextPage?: string | null;
}

export interface TaskImportErrorRow {
  row: number;
  reason: string;
}

export interface TaskImportResponse {
  imported: number;
  skipped: number;
  errors: TaskImportErrorRow[];
}

export interface AssignTasksRequest {
  emails: string[];
}

export interface AssignTasksResponse {
  assigned: string[];
  skipped: string[];
}

export interface CreateTaskRequest {
  taskCode: string;
  taskName: string;
  description?: string;
  sponsor?: string;
  costCentre?: string;
  coeResponsible?: string;
  status?: TaskStatus;
}

export interface UpdateTaskRequest {
  taskName?: string;
  description?: string;
  sponsor?: string;
  costCentre?: string;
  coeResponsible?: string;
  status?: TaskStatus;
}
