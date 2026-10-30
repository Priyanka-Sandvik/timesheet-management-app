import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { decodeJwt, isTokenExpired } from "./jwt";
import { clearToken, getAlternateToken, getToken, setAlternateToken, setToken } from "./tokenStorage";
import type { DecodedToken } from "@/types";

interface AuthState {
  token: string | null;
  claims: DecodedToken | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  fullName: string | null;
  /** True when the user holds a token for the other panel (admins only). */
  canSwitchPanel: boolean;
  login: (token: string, fullName?: string, alternateToken?: string | null) => void;
  /** Swaps the active token with the alternate one (admin <-> employee panel). */
  switchPanel: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

const NAME_KEY = "ts_full_name";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => {
    const existing = getToken();
    const decoded = existing ? decodeJwt(existing) : null;
    if (existing && isTokenExpired(decoded)) {
      clearToken();
      return null;
    }
    return existing;
  });
  const [altToken, setAltTokenState] = useState<string | null>(() => getAlternateToken());
  const [fullName, setFullName] = useState<string | null>(() => sessionStorage.getItem(NAME_KEY));

  const claims = useMemo(() => (token ? decodeJwt(token) : null), [token]);

  const login = useCallback((newToken: string, name?: string, alternateToken?: string | null) => {
    setToken(newToken);
    setTokenState(newToken);
    setAlternateToken(alternateToken ?? null);
    setAltTokenState(alternateToken ?? null);
    if (name) {
      sessionStorage.setItem(NAME_KEY, name);
      setFullName(name);
    }
  }, []);

  const switchPanel = useCallback(() => {
    if (!token || !altToken) return;
    setToken(altToken);
    setAlternateToken(token);
    setTokenState(altToken);
    setAltTokenState(token);
  }, [token, altToken]);

  const logout = useCallback(() => {
    clearToken();
    sessionStorage.removeItem(NAME_KEY);
    setTokenState(null);
    setAltTokenState(null);
    setFullName(null);
  }, []);

  const value: AuthState = {
    token,
    claims,
    isAuthenticated: !!token && !isTokenExpired(claims),
    isAdmin: !!claims?.isAdmin,
    fullName,
    canSwitchPanel: !!altToken,
    login,
    switchPanel,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
