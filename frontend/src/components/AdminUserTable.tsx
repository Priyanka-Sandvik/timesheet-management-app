import { useMemo, useState } from "react";
import type { User } from "@/types";
import styles from "./AdminTaskTable.module.css";

interface AdminUserTableProps {
  users: User[];
  onEdit: (user: User) => void;
}

const BASE_COLUMN_COUNT = 7;
const DETAIL_COLUMN_COUNT = 5;

function show(value: string | number | null) {
  return value === null || value === "" ? "-" : value;
}

export function AdminUserTable({ users, onEdit }: AdminUserTableProps) {
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) =>
        u.fullName.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q),
    );
  }, [users, search]);

  // The detail columns appear once any row has "Show details" ticked; only the ticked rows
  // fill them in, the rest stay blank.
  const showDetailColumns = expanded.size > 0;
  const columnCount =
    BASE_COLUMN_COUNT + (showDetailColumns ? DETAIL_COLUMN_COUNT : 0);

  function toggleDetails(email: string, on: boolean) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (on) next.add(email);
      else next.delete(email);
      return next;
    });
  }

  return (
    <div>
      <div className={styles.filterRow}>
        <input
          className={styles.searchInput}
          placeholder="Search by name or email"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* nowrap keeps long names/emails on one line; the wrapper scrolls instead of squashing columns */}
      <div style={{ overflowX: "auto" }}>
        <table className={styles.table} style={{ whiteSpace: "nowrap" }}>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Start Date</th>
              <th>End Date</th>
              <th>IsActive</th>
              <th>Show details</th>
              {showDetailColumns && (
                <>
                  <th>Vendor</th>
                  <th>Vendor Email</th>
                  <th>Vendor Phone</th>
                  <th>Vendor Rate</th>
                  <th>Sandvik Rate</th>
                </>
              )}
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((u) => {
              const open = expanded.has(u.email);
              return (
                <tr key={u.email}>
                  <td>{u.fullName}</td>
                  <td>{u.email}</td>
                  <td>{show(u.startDate)}</td>
                  <td>{show(u.endDate)}</td>
                  <td>
                    <input
                      type="checkbox"
                      checked={u.isActive}
                      readOnly
                      disabled
                      aria-label={`Active status for ${u.email} (set by end date)`}
                      title="Derived from the end date"
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      checked={open}
                      onChange={(e) => toggleDetails(u.email, e.target.checked)}
                      aria-label={`Show details for ${u.email}`}
                    />
                  </td>
                  {showDetailColumns && (
                    <>
                      <td>{open ? show(u.vendor) : ""}</td>
                      <td>{open ? show(u.vendorEmail) : ""}</td>
                      <td>{open ? show(u.vendorPhone) : ""}</td>
                      <td>{open ? show(u.vendorRate) : ""}</td>
                      <td>{open ? show(u.sandvikRate) : ""}</td>
                    </>
                  )}
                  <td>
                    <div className={styles.actionsCell}>
                      <button
                        className={styles.actionBtn}
                        onClick={() => onEdit(u)}
                      >
                        Edit
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {visible.length === 0 && (
              <tr>
                <td
                  colSpan={columnCount}
                  style={{
                    textAlign: "center",
                    color: "var(--color-text-muted)",
                    padding: 24,
                  }}
                >
                  No users found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
