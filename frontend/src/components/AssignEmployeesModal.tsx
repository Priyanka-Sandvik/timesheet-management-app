import { useMemo, useState } from "react";
import type { User } from "@/types";
import styles from "./ModalShared.module.css";

interface AssignEmployeesModalProps {
  taskCode: string;
  taskLabel: string;
  allUsers: User[];
  assignedEmails: string[];
  onClose: () => void;
  onAssign: (taskCode: string, emails: string[]) => Promise<void>;
  onUnassign: (taskCode: string, email: string) => Promise<void>;
}

export function AssignEmployeesModal({
  taskCode,
  taskLabel,
  allUsers,
  assignedEmails,
  onClose,
  onAssign,
  onUnassign,
}: AssignEmployeesModalProps) {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [currentlyAssigned, setCurrentlyAssigned] = useState<string[]>(assignedEmails);
  const [saving, setSaving] = useState(false);
  const [removingEmail, setRemovingEmail] = useState<string | null>(null);

  const candidates = useMemo(() => {
    const q = search.trim().toLowerCase();
    return allUsers.filter(
      (u) =>
        !currentlyAssigned.includes(u.email) &&
        (q === "" || u.fullName.toLowerCase().includes(q) || u.email.toLowerCase().includes(q))
    );
  }, [allUsers, search, currentlyAssigned]);

  function toggleSelected(email: string) {
    setSelected((prev) => (prev.includes(email) ? prev.filter((e) => e !== email) : [...prev, email]));
  }

  async function handleAssign() {
    if (selected.length === 0) return;
    setSaving(true);
    try {
      await onAssign(taskCode, selected);
      setCurrentlyAssigned((prev) => [...prev, ...selected]);
      setSelected([]);
    } finally {
      setSaving(false);
    }
  }

  async function handleUnassign(email: string) {
    setRemovingEmail(email);
    try {
      await onUnassign(taskCode, email);
      setCurrentlyAssigned((prev) => prev.filter((e) => e !== email));
    } finally {
      setRemovingEmail(null);
    }
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.dialog}>
        <h3 className={styles.title}>Assign Employees - {taskLabel}</h3>

        <div className={styles.field}>
          <label className={styles.label}>Currently Assigned</label>
          {currentlyAssigned.length === 0 ? (
            <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>No employees assigned yet.</div>
          ) : (
            <div className={styles.chipList}>
              {currentlyAssigned.map((email) => (
                <span key={email} className={styles.chip}>
                  {email}
                  <button
                    className={styles.chipRemove}
                    onClick={() => handleUnassign(email)}
                    disabled={removingEmail === email}
                    aria-label={`Remove ${email}`}
                  >
                    &times;
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        <div className={styles.field}>
          <label className={styles.label}>Add Employees</label>
          <input
            className={styles.input}
            placeholder="Search by name or email"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className={styles.pickList}>
          {candidates.map((u) => (
            <label key={u.email} className={styles.pickItem}>
              <input
                type="checkbox"
                checked={selected.includes(u.email)}
                onChange={() => toggleSelected(u.email)}
              />
              {u.fullName} ({u.email})
            </label>
          ))}
          {candidates.length === 0 && (
            <div className={styles.pickItem} style={{ color: "var(--color-text-muted)" }}>
              No matching employees.
            </div>
          )}
        </div>

        <div className={styles.actions}>
          <button className={styles.cancelBtn} onClick={onClose}>
            Close
          </button>
          <button className={styles.confirmBtn} onClick={handleAssign} disabled={saving || selected.length === 0}>
            {saving ? "Assigning..." : "Assign"}
          </button>
        </div>
      </div>
    </div>
  );
}
