import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthForm } from "@/components/AuthForm";
import styles from "@/components/AuthForm.module.css";
import { profileApi } from "@/api/profileApi";
import { useAuth } from "@/auth/AuthContext";
import { ApiError } from "@/types/api";

export function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<"login" | "admin" | null>(null);

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSubmitting("login");
    try {
      const response = await profileApi.login({ email, password });
      login(response.access_token);
      // Plain "Log In" always redirects to My Time Sheet, admin or not - UI spec §3.
      navigate("/my-timesheet", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setFormError("Invalid email or password.");
      } else {
        console.error(err);
        setFormError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(null);
    }
  }

  async function handleLoginAsAdmin() {
    setFormError(null);
    setSubmitting("admin");
    try {
      const response = await profileApi.loginAsAdmin({ email, password });
      login(response.access_token);
      // Admin entry point lands on Task Import, not My Time Sheet - UI spec §3.
      navigate("/admin/task-import", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setFormError("Invalid email or password.");
      } else {
        console.error(err);
        setFormError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(null);
    }
  }

  return (
    <AuthForm
      title="Log in"
      subtitle="Sign in with your Sandvik company account."
      error={formError}
      footer={
        <>
          Don&apos;t have an account? <Link to="/register">Create Account</Link>
        </>
      }
    >
      <form onSubmit={handleLogin}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="email">
            Email
          </label>
          <input
            id="email"
            className={styles.input}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
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
            />
            <button type="button" className={styles.toggleBtn} onClick={() => setShowPassword((v) => !v)}>
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
        </div>

        {/* No "Forgot password?" affordance anywhere, per UI spec §3. */}

        <button className={styles.primaryBtn} type="submit" disabled={submitting !== null}>
          {submitting === "login" ? "Logging In..." : "Log In"}
        </button>
        <button
          className={styles.secondaryBtn}
          type="button"
          disabled={submitting !== null}
          onClick={handleLoginAsAdmin}
        >
          {submitting === "admin" ? "Logging In..." : "Login as Admin"}
        </button>
      </form>
    </AuthForm>
  );
}
