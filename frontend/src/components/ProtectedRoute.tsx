import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { Header } from "./Header";

export function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
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
