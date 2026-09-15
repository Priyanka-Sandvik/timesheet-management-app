import { formatDayHeader, toIsoDate } from "@/utils/date";
import type { TimesheetEntry } from "@/types";
import styles from "./TimesheetGrid.module.css";

interface TimesheetGridProps {
  weekDays: Date[];
  dailyTotals: Record<string, number>;
  weeklyTotal: number;
  entries: TimesheetEntry[];
}

export function TimesheetGrid({ weekDays, dailyTotals, weeklyTotal, entries }: TimesheetGridProps) {
  const hasData = weeklyTotal > 0;

  // Backend only reports total hours per day; derive the per-day task count client-side
  // from the entries list (one entry per assigned task per day).
  const taskCountsByDate = entries.reduce<Record<string, number>>((acc, entry) => {
    acc[entry.entryDate] = (acc[entry.entryDate] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className={styles.wrapper}>
      <div className={styles.daysRow}>
        {weekDays.map((day) => {
          const iso = toIsoDate(day);
          const hours = dailyTotals[iso] ?? 0;
          const taskCount = taskCountsByDate[iso] ?? 0;
          return (
            <div key={iso} className={styles.dayCol}>
              <div className={styles.dayHeader}>{formatDayHeader(day)}</div>
              {hours > 0 ? (
                <div className={styles.dayValue}>
                  <div className={styles.hours}>{hours} Hrs</div>
                  <div className={styles.taskCount}>{taskCount} Tasks</div>
                </div>
              ) : (
                <div className={styles.na}>-NA-</div>
              )}
            </div>
          );
        })}
      </div>

      <div className={styles.breakdownPanel}>
        <div className={styles.breakdownTitle}>
          Time Sheet breakdown{hasData && <span className={styles.breakdownTotal}>{weeklyTotal} hrs</span>}
        </div>
        {hasData ? (
          <div className={styles.bar}>
            <div className={styles.barFill} style={{ width: "100%" }}>
              Project Tasks ({weeklyTotal} hrs)
            </div>
          </div>
        ) : (
          <div className={styles.noData}>No data to display</div>
        )}
      </div>
    </div>
  );
}
