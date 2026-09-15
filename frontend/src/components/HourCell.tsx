import { useEffect, useState } from "react";
import styles from "./HourCell.module.css";

interface HourCellProps {
  value: number;
  readOnly?: boolean;
  onCommit: (newValue: number) => void;
}

function isValidHours(n: number): boolean {
  if (isNaN(n)) return false;
  if (n < 0 || n > 24) return false;
  // must be a 0.25 increment
  const scaled = Math.round(n * 4);
  return Math.abs(scaled - n * 4) < 1e-6;
}

export function HourCell({ value, readOnly, onCommit }: HourCellProps) {
  const [text, setText] = useState(String(value));
  const [error, setError] = useState(false);

  useEffect(() => {
    setText(String(value));
    setError(false);
  }, [value]);

  function handleBlur() {
    if (text.trim() === "") {
      setText(String(value));
      setError(false);
      return;
    }
    const parsed = Number(text);
    if (!isValidHours(parsed)) {
      setError(true);
      return;
    }
    setError(false);
    if (parsed !== value) {
      onCommit(parsed);
    }
  }

  if (readOnly) {
    return <div className={styles.readOnlyCell}>{value}</div>;
  }

  return (
    <div className={styles.cellWrapper}>
      <input
        className={`${styles.input} ${error ? styles.inputError : ""}`}
        type="number"
        min={0}
        max={24}
        step={0.25}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={handleBlur}
        title={error ? "Hours must be between 0 and 24, in 0.25 increments" : undefined}
      />
      {error && <div className={styles.tooltip}>0-24, steps of 0.25</div>}
    </div>
  );
}
