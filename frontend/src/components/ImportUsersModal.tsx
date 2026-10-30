import { useRef, useState } from "react";
import type { UserImportResponse } from "@/types";
import { useToast } from "./ToastContext";
import modalStyles from "./ModalShared.module.css";
import styles from "./AdminTaskImportPanel.module.css";

interface ImportUsersModalProps {
  onClose: () => void;
  onImport: (file: File) => Promise<UserImportResponse>;
}

const ACCEPTED_EXTENSIONS = [".csv", ".xlsx"];

export function ImportUsersModal({ onClose, onImport }: ImportUsersModalProps) {
  const { showToast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UserImportResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFiles(fileList: FileList | null) {
    const f = fileList?.[0];
    if (!f) return;
    if (!ACCEPTED_EXTENSIONS.some((ext) => f.name.toLowerCase().endsWith(ext))) {
      showToast("Only .csv or .xlsx files are accepted.");
      return;
    }
    setFile(f);
    setResult(null);
  }

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    try {
      setResult(await onImport(file));
      setFile(null);
    } catch {
      // The caller has already shown the error.
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className={modalStyles.overlay}>
      <div className={modalStyles.dialog} style={{ width: 560 }}>
        <h3 className={modalStyles.title}>Import Users</h3>

        <div className={styles.referenceBox}>
          <div className={styles.referenceTitle}>Column layout</div>
          <div className={styles.referenceColumns}>
            Name*, Email*, Start Date, End Date, Vendor, Vendor Email, Vendor Phone, Vendor Rate, Sandvik Rate
          </div>
          <div style={{ marginTop: 6, color: "var(--color-text-muted)" }}>
            * required. Other columns may be missing or blank. Dates as YYYY-MM-DD. Users whose email already exists are
            updated with the values filled in the file.
          </div>
        </div>

        <div className={styles.dropzone} style={{ padding: "24px 20px" }} onClick={() => inputRef.current?.click()}>
          <button type="button" className={styles.browseBtn}>
            Browse Files (.csv / .xlsx)
          </button>
          <input
            ref={inputRef}
            type="file"
            className={styles.fileInput}
            accept=".csv,.xlsx"
            onChange={(e) => handleFiles(e.target.files)}
          />
          {file && <div className={styles.selectedFile}>Selected: {file.name}</div>}
        </div>

        {result && (
          <div className={styles.summary} style={{ marginTop: 16 }}>
            <div className={styles.summaryText}>
              {result.created} users created, {result.updated} updated, {result.errors.length} errors
            </div>
            {result.errors.length > 0 && (
              <table className={styles.errorTable}>
                <thead>
                  <tr>
                    <th>Row</th>
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {result.errors.map((e, i) => (
                    <tr key={i}>
                      <td>Row {e.row}</td>
                      <td>{e.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        <div className={modalStyles.actions}>
          <button className={modalStyles.cancelBtn} onClick={onClose}>
            {result ? "Close" : "Cancel"}
          </button>
          <button className={modalStyles.confirmBtn} onClick={handleUpload} disabled={!file || uploading}>
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>
      </div>
    </div>
  );
}
