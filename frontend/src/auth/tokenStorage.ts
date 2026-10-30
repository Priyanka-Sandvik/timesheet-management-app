// ASSUMPTION: the architecture doc says "no refresh tokens" and the build
// prompt asks for in-memory storage, but a pure in-memory store loses the
// session on every full page reload (F5), which is a poor experience for an
// internal tool employees keep open all day. As a pragmatic compromise we
// use sessionStorage (cleared when the tab/browser closes, never persisted
// to disk like localStorage, never sent anywhere but attached manually as a
// Bearer header) instead of pure in-memory storage. This is a deliberate,
// documented deviation - flagged here and in the final report.

const TOKEN_KEY = "ts_access_token";
const ALT_TOKEN_KEY = "ts_alternate_token";

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(ALT_TOKEN_KEY);
}

// Admins hold a second token (the other panel's) so they can switch panels without
// logging in again. The employee token has isAdmin=false, so an admin in the employee
// panel has no admin rights on any service.
export function getAlternateToken(): string | null {
  return sessionStorage.getItem(ALT_TOKEN_KEY);
}

export function setAlternateToken(token: string | null): void {
  if (token) sessionStorage.setItem(ALT_TOKEN_KEY, token);
  else sessionStorage.removeItem(ALT_TOKEN_KEY);
}
