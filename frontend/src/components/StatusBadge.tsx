import styles from "./StatusBadge.module.css";

type StatusValue = "Pending" | "Submitted" | "Open" | "OnHold" | "Closed" | "Active" | "Inactive";

const VARIANT_MAP: Record<StatusValue, "warning" | "success" | "neutral" | "danger"> = {
  Pending: "warning",
  Submitted: "success",
  Open: "success",
  OnHold: "warning",
  Closed: "neutral",
  Active: "success",
  Inactive: "danger",
};

const LABEL_MAP: Partial<Record<StatusValue, string>> = {
  OnHold: "On Hold",
};

export function StatusBadge({ status }: { status: StatusValue }) {
  const variant = VARIANT_MAP[status] ?? "neutral";
  const label = LABEL_MAP[status] ?? status;
  return <span className={`${styles.badge} ${styles[variant]}`}>{label}</span>;
}
