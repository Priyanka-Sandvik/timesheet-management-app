import { useState } from "react";
import { formatWeekRangeLabel, getWeekStart, parseIsoDate, toIsoDate } from "@/utils/date";
import styles from "./WeekNavigator.module.css";

interface WeekNavigatorProps {
  weekStart: Date;
  onChangeWeekStart: (weekStart: Date) => void;
}

export function WeekNavigator({ weekStart, onChangeWeekStart }: WeekNavigatorProps) {
  const [pickerOpen, setPickerOpen] = useState(false);

  function goPrev() {
    const d = new Date(weekStart);
    d.setDate(d.getDate() - 7);
    onChangeWeekStart(d);
  }

  function goNext() {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + 7);
    onChangeWeekStart(d);
  }

  function goToCurrentWeek() {
    onChangeWeekStart(getWeekStart(new Date()));
  }

  function handlePickDate(value: string) {
    if (!value) return;
    const picked = parseIsoDate(value);
    onChangeWeekStart(getWeekStart(picked));
    setPickerOpen(false);
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.row}>
        <button className={styles.arrowBtn} onClick={goPrev} aria-label="Previous week">
          &lsaquo;
        </button>
        <div className={styles.rangeWrapper}>
          <button className={styles.rangeLabel} onClick={() => setPickerOpen((v) => !v)}>
            {formatWeekRangeLabel(weekStart)} <span className={styles.caret}>&#9662;</span>
          </button>
          {pickerOpen && (
            <input
              type="date"
              className={styles.datePicker}
              value={toIsoDate(weekStart)}
              onChange={(e) => handlePickDate(e.target.value)}
              autoFocus
              onBlur={() => setPickerOpen(false)}
            />
          )}
        </div>
        <button className={styles.arrowBtn} onClick={goNext} aria-label="Next week">
          &rsaquo;
        </button>
      </div>
      <button className={styles.currentWeekLink} onClick={goToCurrentWeek}>
        Go to Current Week
      </button>
    </div>
  );
}
