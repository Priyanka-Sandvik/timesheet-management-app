// Matches architecture doc §6 Timesheet entity and §8.3 Timelog Service API contracts.

export type TimesheetStatus = "Pending" | "Submitted";

export interface TimesheetEntry {
  taskCode: string;
  taskName: string;
  projectName: string | null;
  entryDate: string; // YYYY-MM-DD
  hours: number;
  notes?: string | null;
}

export interface TimesheetResponse {
  weekStart: string;
  weekEnd: string;
  status: TimesheetStatus;
  entries: TimesheetEntry[];
  // Keyed by ISO date (YYYY-MM-DD) -> total hours logged that day. Matches the Timelog
  // Service's `TimesheetGridResponse.dailyTotals: dict[str, float]` exactly.
  dailyTotals: Record<string, number>;
  weeklyTotal: number;
}

export interface TimesheetEntryUpsert {
  taskCode: string;
  entryDate: string;
  hours: number;
  notes?: string;
}

export interface BulkUpsertRequest {
  weekStart: string;
  entries: TimesheetEntryUpsert[];
}

export interface BulkUpsertResponse {
  saved: number;
}

export interface GenerateResponse {
  rowsCreated: number;
}

export interface CopyPreviousResponse {
  rowsCopied: number;
}

export interface SubmitResponse {
  status: "Submitted";
}
