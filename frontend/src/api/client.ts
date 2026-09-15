import { getToken, clearToken } from "@/auth/tokenStorage";
import { ApiError, type ApiErrorEnvelope } from "@/types/api";

export const SERVICE_BASE_URLS = {
  profile: import.meta.env.VITE_PROFILE_SERVICE_BASE_URL,
  task: import.meta.env.VITE_TASK_SERVICE_BASE_URL,
  timelog: import.meta.env.VITE_TIMELOG_SERVICE_BASE_URL,
} as const;

type ServiceName = keyof typeof SERVICE_BASE_URLS;

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
  auth?: boolean; // attach Bearer token, default true
  isFormData?: boolean;
}

// Set by the app root once, so a 401 anywhere can force a redirect to /login
// without every call site needing to know about routing.
let onUnauthorized: (() => void) | null = null;
export function registerUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

function buildUrl(base: string, path: string, query?: RequestOptions["query"]): string {
  const url = new URL(path.replace(/^\//, ""), base.endsWith("/") ? base : base + "/");
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    });
  }
  return url.toString();
}

async function request<T>(service: ServiceName, path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, query, auth = true, isFormData = false } = options;
  const base = SERVICE_BASE_URLS[service];
  const url = buildUrl(base, path, query);

  const headers: Record<string, string> = {};
  if (!isFormData) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : isFormData ? (body as FormData) : JSON.stringify(body),
  });

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  const isJson = response.headers.get("content-type")?.includes("application/json");

  if (!response.ok) {
    if (response.status === 401) {
      clearToken();
      onUnauthorized?.();
    }
    if (isJson) {
      const envelope = (await response.json()) as ApiErrorEnvelope;
      if (envelope?.error) {
        throw new ApiError(response.status, envelope.error);
      }
    }
    throw new ApiError(response.status, {
      code: "UNKNOWN_ERROR",
      message: `Request failed with status ${response.status}`,
    });
  }

  if (isJson) {
    return (await response.json()) as T;
  }
  return undefined as unknown as T;
}

/** For binary/streamed responses (e.g. the monthly export .xlsx). */
async function requestBlob(
  service: ServiceName,
  path: string,
  options: RequestOptions = {}
): Promise<{ blob: Blob; filename: string | null }> {
  const { method = "GET", query, auth = true } = options;
  const base = SERVICE_BASE_URLS[service];
  const url = buildUrl(base, path, query);

  const headers: Record<string, string> = {};
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, { method, headers });

  if (!response.ok) {
    if (response.status === 401) {
      clearToken();
      onUnauthorized?.();
    }
    const isJson = response.headers.get("content-type")?.includes("application/json");
    if (isJson) {
      const envelope = (await response.json()) as ApiErrorEnvelope;
      if (envelope?.error) {
        throw new ApiError(response.status, envelope.error);
      }
    }
    throw new ApiError(response.status, {
      code: "UNKNOWN_ERROR",
      message: `Request failed with status ${response.status}`,
    });
  }

  const disposition = response.headers.get("content-disposition");
  const match = disposition?.match(/filename="?([^"]+)"?/);
  const blob = await response.blob();
  return { blob, filename: match ? match[1] : null };
}

export const apiClient = { request, requestBlob };
