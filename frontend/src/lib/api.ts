import { shouldSkipMsalInit } from "@/lib/auth/public-routes";
import { getAccessToken } from "@/lib/auth/token-provider";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getApiUrl() {
  return API_URL;
}

export type ApiResponse<T> = {
  success: boolean;
  data: T;
  meta?: Record<string, unknown>;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<ApiResponse<T>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  let authToken = token;
  if (authToken === undefined) {
    const skipAuth =
      typeof window !== "undefined" && shouldSkipMsalInit(window.location.pathname);
    authToken = skipAuth ? null : await getAccessToken();
  }
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  const payload = await response.json();
  if (!response.ok) {
    const message = payload?.detail?.error?.message || payload?.detail || "Request failed";
    throw new ApiError(response.status, typeof message === "string" ? message : JSON.stringify(message));
  }
  return payload;
}
