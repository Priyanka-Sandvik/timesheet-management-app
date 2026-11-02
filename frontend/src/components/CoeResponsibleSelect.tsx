import type { User } from "@/types";
import styles from "./ModalShared.module.css";

interface CoeResponsibleSelectProps {
  users: User[];
  /** The stored value: the chosen user's email (older tasks may hold free text). */
  value: string;
  onChange: (email: string) => void;
}

const sameEmail = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase();

/** Name to show for a stored CoE value; falls back to the raw value for free text or unknown users. */
export function coeDisplayName(users: User[], value: string | null | undefined): string {
  if (!value) return "-";
  return users.find((u) => sameEmail(u.email, value))?.fullName ?? value;
}

export function CoeResponsibleSelect({ users, value, onChange }: CoeResponsibleSelectProps) {
  const activeUsers = users.filter((u) => u.isActive).sort((a, b) => a.fullName.localeCompare(b.fullName));
  // Keep the current value selectable even if that person is no longer in the active list
  // (inactive user, or older free text), so opening Edit never silently clears it.
  const currentMissing = value !== "" && !activeUsers.some((u) => sameEmail(u.email, value));

  return (
    <select className={styles.input} value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">- None -</option>
      {currentMissing && <option value={value}>{coeDisplayName(users, value)}</option>}
      {activeUsers.map((u) => (
        <option key={u.email} value={u.email}>
          {u.fullName}
        </option>
      ))}
    </select>
  );
}
