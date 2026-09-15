import type { DecodedToken } from "@/types";

/**
 * Decodes a JWT payload WITHOUT verifying the signature. This is only ever
 * used client-side to drive UI decisions (e.g. show/hide admin nav items).
 * Every actual admin/employee authorization check is enforced server-side
 * by the owning microservice, per architecture doc §9.
 */
export function decodeJwt(token: string): DecodedToken | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = payload.padEnd(payload.length + ((4 - (payload.length % 4)) % 4), "=");
    const json = decodeURIComponent(
      atob(padded)
        .split("")
        .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
        .join("")
    );
    return JSON.parse(json) as DecodedToken;
  } catch {
    return null;
  }
}

export function isTokenExpired(decoded: DecodedToken | null): boolean {
  if (!decoded || !decoded.exp) return true;
  return decoded.exp * 1000 <= Date.now();
}
