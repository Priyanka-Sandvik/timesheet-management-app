import { apiClient } from "./client";
import type {
  BulkUpsertRequest,
  BulkUpsertResponse,
  CopyPreviousResponse,
  GenerateResponse,
  SubmitResponse,
  TimesheetResponse,
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

  copyPrevious(weekStart: string) {
    return apiClient.request<CopyPreviousResponse>("timelog", "/api/v1/timesheet/copy-previous", {
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
};
