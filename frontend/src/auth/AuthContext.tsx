import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { decodeJwt, isTokenExpired } from "./jwt";
import { clearToken, getToken, setToken } from "./tokenStorage";
import type { DecodedToken } from "@/types";

interface AuthState {
  token: string | null;
  claims: DecodedToken | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  fullName: string | null;
  login: (token: string, fullName?: string) => void;
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
  const [fullName, setFullName] = useState<string | null>(() => sessionStorage.getItem(NAME_KEY));

  const claims = useMemo(() => (token ? decodeJwt(token) : null), [token]);

  const login = useCallback((newToken: string, name?: string) => {
    setToken(newToken);
    setTokenState(newToken);
    if (name) {
      sessionStorage.setItem(NAME_KEY, name);
      setFullName(name);
    }
  }, []);

  const logout = useCallback(() => {
    clearToken();
    sessionStorage.removeItem(NAME_KEY);
    setTokenState(null);
    setFullName(null);
  }, []);

  const value: AuthState = {
    token,
    claims,
    isAuthenticated: !!token && !isTokenExpired(claims),
    isAdmin: !!claims?.isAdmin,
    fullName,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
