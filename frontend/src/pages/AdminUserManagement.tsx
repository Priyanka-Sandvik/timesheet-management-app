import { useCallback, useEffect, useState } from "react";
import { profileApi } from "@/api/profileApi";
import type { User } from "@/types";
import { AdminUserTable } from "@/components/AdminUserTable";
import { useToast } from "@/components/ToastContext";

export function AdminUserManagement() {
  const { showToast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  const loadUsers = useCallback(async () => {
    try {
      const response = await profileApi.adminListUsers();
      setUsers(response.users);
    } catch (err) {
      console.error(err);
      showToast("Failed to load users.");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  async function handleToggleActive(email: string, next: boolean) {
    // Optimistic update with rollback on failure, per UI spec §7.
    const previous = users;
    setUsers((prev) => prev.map((u) => (u.email === email ? { ...u, isActive: next } : u)));
    try {
      await profileApi.adminSetUserStatus(email, { isActive: next });
    } catch (err) {
      setUsers(previous);
      console.error(err);
      showToast("Failed to update user status.");
    }
  }

  if (loading) return <p style={{ color: "var(--color-text-muted)" }}>Loading...</p>;

  return <AdminUserTable users={users} onToggleActive={handleToggleActive} />;
}
