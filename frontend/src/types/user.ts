// Matches architecture doc §6 Users entity and §8.1 Profile Service API contracts.

export interface User {
  email: string;
  fullName: string;
  isActive: boolean;
  createdAt: string;
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
}

export interface AdminUsersResponse {
  users: User[];
}

export interface UpdateUserStatusRequest {
  isActive: boolean;
}

export interface UpdateUserStatusResponse {
  email: string;
  isActive: boolean;
}

// Decoded JWT payload shape (client-side decode only, for UI routing decisions).
export interface DecodedToken {
  sub: string;
  isAdmin: boolean;
  exp: number;
  iat?: number;
  [key: string]: unknown;
}
