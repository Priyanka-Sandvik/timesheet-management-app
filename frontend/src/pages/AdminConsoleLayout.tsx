import { NavLink, Outlet } from "react-router-dom";
import styles from "./AdminConsoleLayout.module.css";

const TABS = [
  { to: "/admin/task-import", label: "Task Import" },
  { to: "/admin/task-management", label: "Task Management" },
  { to: "/admin/user-management", label: "User Management" },
  { to: "/admin/monthly-export", label: "Monthly Export" },
];

export function AdminConsoleLayout() {
  return (
    <div>
      <div className={styles.header}>
        <h1 className={styles.title}>Admin Console</h1>
      </div>
      <nav className={styles.tabs}>
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) => `${styles.tab} ${isActive ? styles.tabActive : ""}`}
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <div className={styles.content}>
        <Outlet />
      </div>
    </div>
  );
}
