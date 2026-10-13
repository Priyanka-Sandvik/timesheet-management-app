import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { Header } from "./Header";

export function ProtectedRoute() {
  const { isAuthenticated, isAdmin } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (isAdmin) {
    // Admins are fixed config accounts, not employees - they never have a timesheet.
    return <Navigate to="/admin/task-import" replace />;
  }
  return (
    <div className="app-shell">
      <Header />
      <div className="page-content">
        <Outlet />
      </div>
    </div>
  );
}

export function AdminRoute() {
  const { isAuthenticated, isAdmin } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (!isAdmin) {
    return <Navigate to="/my-timesheet" replace />;
  }
  return (
    <div className="app-shell">
      <Header />
      <div className="page-content">
        <Outlet />
      </div>
    </div>
  );
}
