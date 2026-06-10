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

export function extractApiErrorMessage(
  payload: unknown,
  fallback = "Request failed",
): string {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const body = payload as Record<string, unknown>;
  const detail = body.detail;
  const error = body.error;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (detail && typeof detail === "object") {
    const detailObj = detail as Record<string, unknown>;
    const nestedError = detailObj.error;
    if (nestedError && typeof nestedError === "object") {
      const message = (nestedError as { message?: unknown }).message;
      if (typeof message === "string" && message.trim()) {
        return message;
      }
    }
    if (typeof detailObj.message === "string" && detailObj.message.trim()) {
      return detailObj.message;
    }
  }

  if (error && typeof error === "object") {
    const message = (error as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }

  if (typeof body.message === "string" && body.message.trim()) {
    return body.message;
  }

  return fallback;
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

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Network request failed";
    throw new ApiError(0, message);
  }

  const rawBody = await response.text();
  let payload: unknown = null;
  if (rawBody) {
    try {
      payload = JSON.parse(rawBody);
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    const fallback = rawBody?.trim() || response.statusText || "Request failed";
    throw new ApiError(response.status, extractApiErrorMessage(payload, fallback));
  }

  if (payload === null) {
    throw new ApiError(response.status, "Empty response from server");
  }

  return payload as ApiResponse<T>;
}
