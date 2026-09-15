import { useMemo } from "react";
import type { TimesheetEntry } from "@/types";
import { formatDayHeader, toIsoDate } from "@/utils/date";
import { HourCell } from "./HourCell";
import styles from "./LoggedTimeCardsTable.module.css";

interface TaskRow {
  taskCode: string;
  taskName: string;
  projectName: string | null;
  hoursByDate: Record<string, number>;
}

interface LoggedTimeCardsTableProps {
  entries: TimesheetEntry[];
  weekDays: Date[];
  readOnly: boolean;
  removedTaskCodes: Set<string>;
  onHourChange: (taskCode: string, entryDate: string, hours: number) => void;
  onRemoveTask: (taskCode: string) => void;
}

export function LoggedTimeCardsTable({
  entries,
  weekDays,
  readOnly,
  removedTaskCodes,
  onHourChange,
  onRemoveTask,
}: LoggedTimeCardsTableProps) {
  const rows = useMemo<TaskRow[]>(() => {
    const map = new Map<string, TaskRow>();
    for (const entry of entries) {
      let row = map.get(entry.taskCode);
      if (!row) {
        row = {
          taskCode: entry.taskCode,
          taskName: entry.taskName,
          projectName: entry.projectName,
          hoursByDate: {},
        };
        map.set(entry.taskCode, row);
      }
      row.hoursByDate[entry.entryDate] = entry.hours;
    }
    return Array.from(map.values());
  }, [entries]);

  // ASSUMPTION: the architecture doc's §8.3 Timelog contract has no dedicated
  // "delete entries" route. Rather than invent a new backend endpoint outside
  // the documented contract, the remove icon zeroes out all 7 days for that
  // task via the existing PUT /api/v1/timesheet/entries bulk-upsert. The row
  // is then hidden client-side (tracked in `removedTaskCodes`, per UI spec
  // §4.3) - functionally equivalent to "removed from this week's sheet".
  //
  // This must NOT be inferred from "all hours are 0", because every row starts
  // at 0 hours immediately after Generate/Copy - inferring removal from that
  // would hide freshly generated rows before the employee ever gets a chance
  // to enter hours.
  const visibleRows = rows.filter((row) => !removedTaskCodes.has(row.taskCode));

  const dayIsoList = weekDays.map(toIsoDate);

  const columnTotals = dayIsoList.map((iso) =>
    visibleRows.reduce((sum, row) => sum + (row.hoursByDate[iso] ?? 0), 0)
  );
  const grandTotal = columnTotals.reduce((a, b) => a + b, 0);

  if (visibleRows.length === 0) {
    return null;
  }

  return (
    <div className={styles.tableWrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.taskCol}>Task</th>
            <th>Project time category</th>
            <th>Resource plan</th>
            {weekDays.map((day) => (
              <th key={toIsoDate(day)} className={styles.dayCol}>
                {formatDayHeader(day)}
              </th>
            ))}
            <th className={styles.totalCol}>Total</th>
            <th className={styles.actionCol} aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row) => {
            const rowTotal = dayIsoList.reduce((sum, iso) => sum + (row.hoursByDate[iso] ?? 0), 0);
            return (
              <tr key={row.taskCode}>
                <td className={styles.taskCol}>
                  <div className={styles.taskName}>
                    {row.projectName ? `${row.projectName} - ${row.taskName}` : row.taskName}
                  </div>
                  <div className={styles.taskCode}>{row.taskCode}</div>
                </td>
                <td className={styles.muted}>None</td>
                <td className={styles.muted}>None</td>
                {dayIsoList.map((iso) => (
                  <td key={iso} className={styles.dayCol}>
                    <HourCell
                      value={row.hoursByDate[iso] ?? 0}
                      readOnly={readOnly}
                      onCommit={(hours) => onHourChange(row.taskCode, iso, hours)}
                    />
                  </td>
                ))}
                <td className={styles.totalCol}>{rowTotal}</td>
                <td className={styles.actionCol}>
                  {!readOnly && (
                    <button
                      className={styles.removeBtn}
                      title="Remove this task from this week's sheet"
                      onClick={() => onRemoveTask(row.taskCode)}
                    >
                      &#8854;
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr>
            <td className={styles.taskCol} />
            <td />
            <td />
            {columnTotals.map((total, i) => (
              <td key={i} className={styles.dayCol}>
                <strong>{total}</strong>
              </td>
            ))}
            <td className={styles.totalCol}>
              <strong>{grandTotal}</strong>
            </td>
            <td className={styles.actionCol} />
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
