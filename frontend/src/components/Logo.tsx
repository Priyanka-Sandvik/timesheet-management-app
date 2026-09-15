import sandvikLogo from "@/assets/sandvik-logo.svg";
import styles from "./Logo.module.css";

export function Logo() {
  return (
    <div className={styles.logo}>
      <img className={styles.mark} src={sandvikLogo} alt="Sandvik" />
    </div>
  );
}
