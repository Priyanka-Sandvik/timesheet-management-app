import type { TimesheetStatus } from "@/types";
import styles from "./StatusBadge.module.css";

interface StatusDropdownProps {
  value: TimesheetStatus;
  onChange: (next: TimesheetStatus) => void;
  disabled?: boolean;
}

const VARIANT_MAP: Record<TimesheetStatus, "warning" | "success"> = {
  Pending: "warning",
  Submitted: "success",
};

export function StatusDropdown({ value, onChange, disabled }: StatusDropdownProps) {
  return (
    <select
      className={`${styles.badge} ${styles[VARIANT_MAP[value]]}`}
      style={{ border: "none", cursor: disabled ? "not-allowed" : "pointer" }}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value as TimesheetStatus)}
      aria-label="Change timesheet status"
    >
      <option value="Pending">Pending</option>
      <option value="Submitted">Submitted</option>
    </select>
  );
}
