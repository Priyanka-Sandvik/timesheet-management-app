import { useMemo, useState } from "react";
import type { User } from "@/types";
import styles from "./AdminTaskTable.module.css";

interface AdminUserTableProps {
  users: User[];
  onToggleActive: (email: string, next: boolean) => void;
}

export function AdminUserTable({ users, onToggleActive }: AdminUserTableProps) {
  const [search, setSearch] = useState("");

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return users;
    return users.filter((u) => u.fullName.toLowerCase().includes(q) || u.email.toLowerCase().includes(q));
  }, [users, search]);

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

      <table className={styles.table}>
        <thead>
          <tr>
            <th>FullName</th>
            <th>Email</th>
            <th>IsActive</th>
            <th>CreatedAt</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((u) => (
            <tr key={u.email}>
              <td>{u.fullName}</td>
              <td>{u.email}</td>
              <td>
                <input
                  type="checkbox"
                  checked={u.isActive}
                  onChange={(e) => onToggleActive(u.email, e.target.checked)}
                  aria-label={`Toggle active status for ${u.email}`}
                />
              </td>
              <td>{new Date(u.createdAt).toLocaleDateString()}</td>
            </tr>
          ))}
          {visible.length === 0 && (
            <tr>
              <td colSpan={4} style={{ textAlign: "center", color: "var(--color-text-muted)", padding: 24 }}>
                No users found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
