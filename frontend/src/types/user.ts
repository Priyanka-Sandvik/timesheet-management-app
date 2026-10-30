// Matches architecture doc §6 Users entity and §8.1 Profile Service API contracts.

export interface User {
  email: string;
  fullName: string;
  isActive: boolean; // derived by the server from endDate
  startDate: string | null; // YYYY-MM-DD
  endDate: string | null; // YYYY-MM-DD
  vendor: string | null;
  vendorEmail: string | null;
  vendorPhone: string | null;
  vendorRate: number | null;
  sandvikRate: number | null;
}

export interface MeResponse {
  email: string;
  fullName: string;
  isAdmin: boolean;
  isActive: boolean;
}

export interface RegisterRequest {
  email: string;
  fullName: string;
  password: string;
}

export interface RegisterResponse {
  email: string;
  fullName: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  alternate_access_token?: string | null;
}

export interface AdminUsersResponse {
  users: User[];
}

export interface UpdateUserRequest {
  fullName: string;
  startDate: string | null;
  endDate: string | null;
  vendor: string | null;
  vendorEmail: string | null;
  vendorPhone: string | null;
  vendorRate: number | null;
  sandvikRate: number | null;
}

export interface CreateUserRequest extends UpdateUserRequest {
  email: string;
}

export interface UserImportResponse {
  created: number;
  updated: number;
  errors: { row: number; reason: string }[];
}

// Decoded JWT payload shape (client-side decode only, for UI routing decisions).
export interface DecodedToken {
  sub: string;
  isAdmin: boolean;
  exp: number;
  iat?: number;
  [key: string]: unknown;
}
