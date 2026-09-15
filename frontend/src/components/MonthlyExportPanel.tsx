import { useState } from "react";
import { timelogApi } from "@/api/timelogApi";
import { getPreviousMonthValue } from "@/utils/date";
import styles from "./MonthlyExportPanel.module.css";

export function MonthlyExportPanel() {
  const [month, setMonth] = useState(getPreviousMonthValue());
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleExport() {
    setExporting(true);
    setError(null);
    try {
      const { blob, filename } = await timelogApi.adminExportMonthly(month);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename ?? `timesheet-export-${month}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      setError("Export is taking longer than expected — please try a narrower month or contact IT.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="month">
          Month
        </label>
        <input
          id="month"
          type="month"
          className={styles.input}
          value={month}
          onChange={(e) => setMonth(e.target.value)}
        />
      </div>
      <p className={styles.note}>Includes all active employees.</p>

      <button className={styles.exportBtn} onClick={handleExport} disabled={exporting}>
        {exporting ? "Exporting..." : "Export"}
      </button>

      {error && <div className={styles.errorBox}>{error}</div>}
    </div>
  );
}
