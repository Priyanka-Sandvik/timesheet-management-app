import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/auth/AuthContext";
import { ToastProvider } from "@/components/ToastContext";
import { ProtectedRoute, AdminRoute } from "@/components/ProtectedRoute";
import { registerUnauthorizedHandler } from "@/api/client";
import { Register } from "@/pages/Register";
import { Login } from "@/pages/Login";
import { MyTimeSheet } from "@/pages/MyTimeSheet";
import { AdminConsoleLayout } from "@/pages/AdminConsoleLayout";
import { AdminTaskImport } from "@/pages/AdminTaskImport";
import { AdminTaskManagement } from "@/pages/AdminTaskManagement";
import { AdminUserManagement } from "@/pages/AdminUserManagement";
import { AdminMonthlyExport } from "@/pages/AdminMonthlyExport";

function UnauthorizedRedirect() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  useEffect(() => {
    registerUnauthorizedHandler(() => {
      logout();
      navigate("/login", { replace: true });
    });
  }, [logout, navigate]);
  return null;
}

function AppRoutes() {
  return (
    <>
      <UnauthorizedRedirect />
      <Routes>
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/my-timesheet" element={<MyTimeSheet />} />
        </Route>

        <Route element={<AdminRoute />}>
          <Route path="/admin" element={<AdminConsoleLayout />}>
            <Route index element={<Navigate to="task-import" replace />} />
            <Route path="task-import" element={<AdminTaskImport />} />
            <Route path="task-management" element={<AdminTaskManagement />} />
            <Route path="user-management" element={<AdminUserManagement />} />
            <Route path="monthly-export" element={<AdminMonthlyExport />} />
          </Route>
        </Route>

        <Route path="/" element={<Navigate to="/my-timesheet" replace />} />
        <Route path="*" element={<Navigate to="/my-timesheet" replace />} />
      </Routes>
    </>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
