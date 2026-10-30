import { useCallback, useEffect, useState } from "react";
import { profileApi } from "@/api/profileApi";
import type { CreateUserRequest, User, UserImportResponse } from "@/types";
import { AdminUserTable } from "@/components/AdminUserTable";
import { ImportUsersModal } from "@/components/ImportUsersModal";
import { UserFormModal } from "@/components/UserFormModal";
import { useToast } from "@/components/ToastContext";
import styles from "./AdminTaskManagement.module.css";

export function AdminUserManagement() {
  const { showToast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [addingUser, setAddingUser] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [importing, setImporting] = useState(false);

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

  async function handleAddUser(body: CreateUserRequest) {
    try {
      await profileApi.adminCreateUser(body);
      showToast("User created.", "success");
      loadUsers();
    } catch (err) {
      console.error(err);
      showToast("Failed to create user (the email may already exist).");
      throw err;
    }
  }

  async function handleEditUser(body: CreateUserRequest) {
    const { email, ...update } = body;
    try {
      await profileApi.adminUpdateUser(email, update);
      showToast("User updated.", "success");
      loadUsers();
    } catch (err) {
      console.error(err);
      showToast("Failed to update user.");
      throw err;
    }
  }

  async function handleImport(file: File): Promise<UserImportResponse> {
    try {
      const result = await profileApi.adminImportUsers(file);
      loadUsers();
      return result;
    } catch (err) {
      console.error(err);
      showToast("User import failed.");
      throw err;
    }
  }

  if (loading) return <p style={{ color: "var(--color-text-muted)" }}>Loading...</p>;

  return (
    <div>
      <div className={styles.toolbar} style={{ gap: 10 }}>
        <button className={styles.addBtn} onClick={() => setImporting(true)}>
          Import Users
        </button>
        <button className={styles.addBtn} onClick={() => setAddingUser(true)}>
          Add User
        </button>
      </div>

      <AdminUserTable users={users} onEdit={setEditingUser} />

      {addingUser && <UserFormModal onClose={() => setAddingUser(false)} onSave={handleAddUser} />}
      {editingUser && (
        <UserFormModal user={editingUser} onClose={() => setEditingUser(null)} onSave={handleEditUser} />
      )}
      {importing && <ImportUsersModal onClose={() => setImporting(false)} onImport={handleImport} />}
    </div>
  );
}
