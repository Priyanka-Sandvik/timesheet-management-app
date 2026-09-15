import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthForm } from "@/components/AuthForm";
import styles from "@/components/AuthForm.module.css";
import { profileApi } from "@/api/profileApi";
import { useAuth } from "@/auth/AuthContext";
import { ApiError } from "@/types/api";

const EMAIL_DOMAIN = "@sandvik.com";

export function Register() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [emailError, setEmailError] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function validateEmail(value: string) {
    if (value.length > 0 && !value.toLowerCase().endsWith(EMAIL_DOMAIN)) {
      setEmailError("Please use your @sandvik.com email");
    } else {
      setEmailError(null);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);

    if (!email.toLowerCase().endsWith(EMAIL_DOMAIN)) {
      setEmailError("Please use your @sandvik.com email");
      return;
    }
    if (password !== confirmPassword) {
      setConfirmError("Passwords do not match");
      return;
    }
    setConfirmError(null);

    setSubmitting(true);
    try {
      await profileApi.register({ email, fullName, password });
      // "usable immediately" - auto-login after registration per UI spec §3.
      const loginResponse = await profileApi.login({ email, password });
      login(loginResponse.access_token, fullName);
      navigate("/my-timesheet", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setFormError("This email is already registered.");
      } else {
        console.error(err);
        setFormError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthForm
      title="Create your account"
      subtitle="Register with your Sandvik company email."
      error={formError}
      footer={
        <>
          Already have an account? <Link to="/login">Log In</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="fullName">
            Full Name
          </label>
          <input
            id="fullName"
            className={styles.input}
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="email">
            Company Email
          </label>
          <input
            id="email"
            className={`${styles.input} ${emailError ? styles.inputError : ""}`}
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              validateEmail(e.target.value);
            }}
            placeholder="firstname.lastname@sandvik.com"
            required
          />
          {emailError && <div className={styles.errorText}>{emailError}</div>}
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="password">
            Password
          </label>
          <div className={styles.passwordRow}>
            <input
              id="password"
              className={styles.input}
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
            <button type="button" className={styles.toggleBtn} onClick={() => setShowPassword((v) => !v)}>
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="confirmPassword">
            Confirm Password
          </label>
          <input
            id="confirmPassword"
            className={`${styles.input} ${confirmError ? styles.inputError : ""}`}
            type={showPassword ? "text" : "password"}
            value={confirmPassword}
            onChange={(e) => {
              setConfirmPassword(e.target.value);
              if (confirmError) setConfirmError(null);
            }}
            required
          />
          {confirmError && <div className={styles.errorText}>{confirmError}</div>}
        </div>

        <button className={styles.primaryBtn} type="submit" disabled={submitting}>
          {submitting ? "Creating Account..." : "Create Account"}
        </button>
      </form>
    </AuthForm>
  );
}
