import { apiClient } from "./client";
import type {
  AdminUsersResponse,
  CreateUserRequest,
  LoginRequest,
  LoginResponse,
  MeResponse,
  RegisterRequest,
  RegisterResponse,
  UpdateUserRequest,
  User,
  UserImportResponse,
} from "@/types";

export const profileApi = {
  register(body: RegisterRequest) {
    return apiClient.request<RegisterResponse>("profile", "/auth/register", {
      method: "POST",
      body,
      auth: false,
    });
  },

  login(body: LoginRequest) {
    return apiClient.request<LoginResponse>("profile", "/auth/login", {
      method: "POST",
      body,
      auth: false,
    });
  },

  loginAsAdmin(body: LoginRequest) {
    return apiClient.request<LoginResponse>("profile", "/auth/login-as-admin", {
      method: "POST",
      body,
      auth: false,
    });
  },

  me() {
    return apiClient.request<MeResponse>("profile", "/api/v1/me");
  },

  adminListUsers(activeOnly?: boolean) {
    return apiClient.request<AdminUsersResponse>("profile", "/admin/users", {
      query: { activeOnly },
    });
  },

  adminCreateUser(body: CreateUserRequest) {
    return apiClient.request<User>("profile", "/admin/users", { method: "POST", body });
  },

  adminUpdateUser(email: string, body: UpdateUserRequest) {
    return apiClient.request<User>("profile", `/admin/users/${encodeURIComponent(email)}`, {
      method: "PUT",
      body,
    });
  },

  adminImportUsers(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.request<UserImportResponse>("profile", "/admin/users/import", {
      method: "POST",
      body: formData,
      isFormData: true,
    });
  },
};
