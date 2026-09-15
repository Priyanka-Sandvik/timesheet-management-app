import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { Logo } from "./Logo";
import styles from "./Header.module.css";

function getInitials(name: string | null, email: string | undefined): string {
  if (name) {
    const parts = name.trim().split(/\s+/);
    return parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("");
  }
  if (email) return email[0]?.toUpperCase() ?? "?";
  return "?";
}

export function Header() {
  const { isAdmin, fullName, claims, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const displayName = fullName ?? claims?.sub ?? "";

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <Logo />
      </div>
      <div className={styles.right} ref={menuRef}>
        <button className={styles.userButton} onClick={() => setMenuOpen((v) => !v)}>
          <span className={styles.avatar}>{getInitials(fullName, claims?.sub as string | undefined)}</span>
          <span className={styles.name}>{displayName}</span>
        </button>
        {menuOpen && (
          <div className={styles.menu}>
            <button className={styles.menuItem} onClick={() => { setMenuOpen(false); navigate("/my-timesheet"); }}>
              My Profile
            </button>
            {isAdmin && (
              <button
                className={styles.menuItem}
                onClick={() => {
                  setMenuOpen(false);
                  navigate("/admin/task-import");
                }}
              >
                Switch to Admin Console
              </button>
            )}
            <button className={styles.menuItem} onClick={handleLogout}>
              Logout
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
