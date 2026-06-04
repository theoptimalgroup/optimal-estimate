import { apiFetch, ApiError } from "@/lib/api";
import type { CurrentUser } from "@/lib/auth/types";

const REGISTRATION_ERROR = "User not registered or inactive. Contact admin.";

export async function getCurrentUser(): Promise<CurrentUser | null> {
  try {
    const response = await apiFetch<CurrentUser>("/api/v1/auth/me");
    return response.data;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    if (error instanceof ApiError && error.status === 403) {
      throw new Error(REGISTRATION_ERROR);
    }
    if (error instanceof ApiError) {
      throw new Error(typeof error.message === "string" ? error.message : "Failed to load current user");
    }
    throw error instanceof Error ? error : new Error("Failed to load current user");
  }
}

export { REGISTRATION_ERROR };
