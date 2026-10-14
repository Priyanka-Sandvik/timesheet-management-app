import { apiClient } from "./client";
import type {
  AdminPeriodStatusResponse,
  AdminSetStatusResponse,
  BulkUpsertRequest,
  BulkUpsertResponse,
  GenerateResponse,
  SubmitResponse,
  TimesheetResponse,
  TimesheetStatus,
} from "@/types";

export const timelogApi = {
  getWeek(userId: string, weekStart: string) {
    return apiClient.request<TimesheetResponse>("timelog", "/api/v1/timesheet", {
      query: { userId, weekStart },
    });
  },

  bulkUpsertEntries(body: BulkUpsertRequest) {
    return apiClient.request<BulkUpsertResponse>("timelog", "/api/v1/timesheet/entries", {
      method: "PUT",
      body,
    });
  },

  generate(weekStart: string) {
    return apiClient.request<GenerateResponse>("timelog", "/api/v1/timesheet/generate", {
      method: "POST",
      query: { weekStart },
    });
  },

  submit(weekStart: string) {
    return apiClient.request<SubmitResponse>("timelog", "/api/v1/timesheet/submit", {
      method: "POST",
      query: { weekStart },
    });
  },

  async adminExportMonthly(month?: string) {
    return apiClient.requestBlob("timelog", "/admin/timesheet/export/monthly", {
      query: { month },
    });
  },

  getAdminPeriodStatuses(month?: string) {
    return apiClient.request<AdminPeriodStatusResponse>("timelog", "/admin/timesheet/status", {
      query: { month },
    });
  },

  setAdminWeekStatus(userId: string, weekStart: string, status: TimesheetStatus) {
    return apiClient.request<AdminSetStatusResponse>(
      "timelog",
      `/admin/timesheet/status/${encodeURIComponent(userId)}`,
      {
        method: "PUT",
        query: { weekStart },
        body: { status },
      },
    );
  },
};
