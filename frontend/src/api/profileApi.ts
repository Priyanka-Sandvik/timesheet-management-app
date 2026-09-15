import { apiClient } from "./client";
import type {
  AdminUsersResponse,
  LoginRequest,
  LoginResponse,
  MeResponse,
  RegisterRequest,
  RegisterResponse,
  UpdateUserStatusRequest,
  UpdateUserStatusResponse,
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

  adminSetUserStatus(email: string, body: UpdateUserStatusRequest) {
    return apiClient.request<UpdateUserStatusResponse>(
      "profile",
      `/admin/users/${encodeURIComponent(email)}/status`,
      { method: "PUT", body }
    );
  },
};
