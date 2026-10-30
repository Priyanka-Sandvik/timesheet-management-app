import { useState } from "react";
import type { CreateUserRequest, User } from "@/types";
import styles from "./ModalShared.module.css";

interface UserFormModalProps {
  // Present when editing an existing user (the email is then read-only), absent when adding.
  user?: User;
  onClose: () => void;
  onSave: (body: CreateUserRequest) => Promise<void>;
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function toNullable(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function toRate(value: string): number | null {
  return value.trim() === "" ? null : Number(value);
}

export function UserFormModal({ user, onClose, onSave }: UserFormModalProps) {
  const isEdit = !!user;
  const [fullName, setFullName] = useState(user?.fullName ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [startDate, setStartDate] = useState(user?.startDate ?? "");
  const [endDate, setEndDate] = useState(user?.endDate ?? "");
  const [vendor, setVendor] = useState(user?.vendor ?? "");
  const [vendorEmail, setVendorEmail] = useState(user?.vendorEmail ?? "");
  const [vendorPhone, setVendorPhone] = useState(user?.vendorPhone ?? "");
  const [vendorRate, setVendorRate] = useState(user?.vendorRate?.toString() ?? "");
  const [sandvikRate, setSandvikRate] = useState(user?.sandvikRate?.toString() ?? "");
  const [saving, setSaving] = useState(false);

  const rateInvalid = (v: string) => v.trim() !== "" && (Number.isNaN(Number(v)) || Number(v) < 0);
  const datesInvalid = !!startDate && !!endDate && endDate < startDate;
  const canSave =
    fullName.trim().length > 0 &&
    EMAIL_PATTERN.test(email.trim()) &&
    !datesInvalid &&
    !rateInvalid(vendorRate) &&
    !rateInvalid(sandvikRate) &&
    !saving;

  async function handleSave() {
    if (!canSave) return;
    setSaving(true);
    try {
      await onSave({
        fullName: fullName.trim(),
        email: email.trim(),
        startDate: startDate || null,
        endDate: endDate || null,
        vendor: toNullable(vendor),
        vendorEmail: toNullable(vendorEmail),
        vendorPhone: toNullable(vendorPhone),
        vendorRate: toRate(vendorRate),
        sandvikRate: toRate(sandvikRate),
      });
      onClose();
    } catch {
      // The caller has already shown the error; keep the dialog open so nothing typed is lost.
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.dialog}>
        <h3 className={styles.title}>{isEdit ? "Edit User" : "Add User"}</h3>
        <div className={styles.row2}>
          <div className={styles.field}>
            <label className={styles.label}>Name *</label>
            <input className={styles.input} value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Email *</label>
            <input
              className={styles.input}
              type="email"
              value={email}
              disabled={isEdit}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
        </div>
        <div className={styles.row2}>
          <div className={styles.field}>
            <label className={styles.label}>Start Date</label>
            <input className={styles.input} type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>End Date</label>
            <input
              className={styles.input}
              type="date"
              value={endDate}
              min={startDate || undefined}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>
        {datesInvalid && <p style={{ color: "var(--color-danger, #c00)", fontSize: 13 }}>End date cannot be before start date.</p>}
        <div className={styles.field}>
          <label className={styles.label}>Vendor</label>
          <input className={styles.input} value={vendor} onChange={(e) => setVendor(e.target.value)} />
        </div>
        <div className={styles.row2}>
          <div className={styles.field}>
            <label className={styles.label}>Vendor Email</label>
            <input className={styles.input} value={vendorEmail} onChange={(e) => setVendorEmail(e.target.value)} />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Vendor Phone</label>
            <input className={styles.input} value={vendorPhone} onChange={(e) => setVendorPhone(e.target.value)} />
          </div>
        </div>
        <div className={styles.row2}>
          <div className={styles.field}>
            <label className={styles.label}>Vendor Rate</label>
            <input
              className={styles.input}
              type="number"
              min="0"
              step="any"
              value={vendorRate}
              onChange={(e) => setVendorRate(e.target.value)}
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Sandvik Rate</label>
            <input
              className={styles.input}
              type="number"
              min="0"
              step="any"
              value={sandvikRate}
              onChange={(e) => setSandvikRate(e.target.value)}
            />
          </div>
        </div>
        <div className={styles.actions}>
          <button className={styles.cancelBtn} onClick={onClose}>
            Cancel
          </button>
          <button className={styles.confirmBtn} onClick={handleSave} disabled={!canSave}>
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
