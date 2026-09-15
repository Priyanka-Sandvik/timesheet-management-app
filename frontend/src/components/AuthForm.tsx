import type { ReactNode } from "react";
import { Logo } from "./Logo";
import styles from "./AuthForm.module.css";

interface AuthFormProps {
  title: string;
  subtitle?: string;
  error?: string | null;
  children: ReactNode;
  footer?: ReactNode;
}

/** Shared card shape for Register/Login, per component inventory in UI spec §9. */
export function AuthForm({ title, subtitle, error, children, footer }: AuthFormProps) {
  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.logoRow}>
          <Logo />
        </div>
        <h1 className={styles.title}>{title}</h1>
        {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        {error && <div className={styles.formError}>{error}</div>}
        {children}
        {footer && <div className={styles.footerRow}>{footer}</div>}
      </div>
    </div>
  );
}
