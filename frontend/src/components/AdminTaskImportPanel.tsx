import { useRef, useState, type DragEvent } from "react";
import { taskApi } from "@/api/taskApi";
import type { TaskImportResponse } from "@/types";
import { useToast } from "./ToastContext";
import styles from "./AdminTaskImportPanel.module.css";

const ACCEPTED_EXTENSIONS = [".csv", ".xlsx"];

export function AdminTaskImportPanel() {
  const { showToast } = useToast();
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<TaskImportResponse | null>(null);
  const [errorsExpanded, setErrorsExpanded] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function isAcceptedFile(f: File) {
    return ACCEPTED_EXTENSIONS.some((ext) => f.name.toLowerCase().endsWith(ext));
  }

  function handleFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    const f = fileList[0];
    if (!isAcceptedFile(f)) {
      showToast("Only .csv or .xlsx files are accepted.");
      return;
    }
    setFile(f);
    setResult(null);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragActive(false);
    handleFiles(e.dataTransfer.files);
  }

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    try {
      const response = await taskApi.adminImport(file);
      setResult(response);
      setFile(null);
    } catch (err) {
      console.error(err);
      showToast("Task import failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.referenceBox}>
        <div className={styles.referenceTitle}>Required column layout</div>
        <div className={styles.referenceColumns}>
          Task Name, Task Code, Description, Sponsor, Cost Centre, CoE Responsible, Status
        </div>
      </div>

      <div
        className={`${styles.dropzone} ${dragActive ? styles.dropzoneActive : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <div className={styles.dropzoneText}>Drag and drop a .csv or .xlsx file here</div>
        <button type="button" className={styles.browseBtn}>
          Browse Files
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

      <div className={styles.actionsRow}>
        <button className={styles.uploadBtn} disabled={!file || uploading} onClick={handleUpload}>
          {uploading ? "Uploading..." : "Upload"}
        </button>
      </div>

      {result && (
        <div className={styles.summary}>
          <div className={styles.summaryText}>
            {result.imported} tasks created, {result.skipped} skipped, {result.errors.length} errors
          </div>
          {result.errors.length > 0 && (
            <>
              <button className={styles.errorToggle} onClick={() => setErrorsExpanded((v) => !v)}>
                {errorsExpanded ? "Hide" : "Show"} row-level errors
              </button>
              {errorsExpanded && (
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
            </>
          )}
        </div>
      )}
    </div>
  );
}
