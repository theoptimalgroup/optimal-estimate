import { apiFetch } from "@/lib/api";
import type { UserRole } from "@/lib/auth/types";

export type ManagedUser = {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  auth_provider: string;
  created_at: string;
  updated_at: string;
};

export type UserListFilters = {
  search?: string;
  role?: UserRole | "";
  active?: boolean;
  limit?: number;
  offset?: number;
};

export type UserListResult = {
  items: ManagedUser[];
  total: number;
  limit: number;
  offset: number;
};

export type UserUpdatePayload = {
  name?: string;
  role?: UserRole;
  is_active?: boolean;
};

export type UserCreatePayload = {
  email: string;
  name: string;
  role: UserRole;
  is_active?: boolean;
};

function normalizeUser(raw: Record<string, unknown>): ManagedUser {
  return {
    id: String(raw.id ?? ""),
    email: String(raw.email ?? ""),
    name: String(raw.name ?? raw.full_name ?? ""),
    role: String(raw.role ?? "client") as UserRole,
    is_active: raw.is_active !== false,
    auth_provider: String(raw.auth_provider ?? "local"),
    created_at: String(raw.created_at ?? ""),
    updated_at: String(raw.updated_at ?? ""),
  };
}

function buildQuery(filters: UserListFilters): string {
  const params = new URLSearchParams();
  if (filters.search?.trim()) params.set("search", filters.search.trim());
  if (filters.role) params.set("role", filters.role);
  if (filters.active !== undefined) params.set("active", String(filters.active));
  params.set("limit", String(filters.limit ?? 50));
  params.set("offset", String(filters.offset ?? 0));
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function listUsers(filters: UserListFilters = {}): Promise<UserListResult> {
  const response = await apiFetch<ManagedUser[]>(`/api/v1/users${buildQuery(filters)}`);
  const meta = response.meta ?? {};
  return {
    items: (response.data ?? []).map((item) => normalizeUser(item as unknown as Record<string, unknown>)),
    total: Number(meta.total ?? 0),
    limit: Number(meta.limit ?? filters.limit ?? 50),
    offset: Number(meta.offset ?? filters.offset ?? 0),
  };
}

export async function getUser(userId: string): Promise<ManagedUser> {
  const response = await apiFetch<ManagedUser>(`/api/v1/users/${userId}`);
  return normalizeUser(response.data as unknown as Record<string, unknown>);
}

export async function updateUser(userId: string, payload: UserUpdatePayload): Promise<ManagedUser> {
  const response = await apiFetch<ManagedUser>(`/api/v1/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return normalizeUser(response.data as unknown as Record<string, unknown>);
}

export async function createUser(payload: UserCreatePayload): Promise<ManagedUser> {
  const response = await apiFetch<ManagedUser>("/api/v1/users", {
    method: "POST",
    body: JSON.stringify({
      email: payload.email.trim(),
      name: payload.name.trim(),
      role: payload.role,
      is_active: payload.is_active ?? true,
    }),
  });
  return normalizeUser(response.data as unknown as Record<string, unknown>);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export const USER_ROLES: UserRole[] = ["admin", "estimator", "manager", "engineer", "client"];

export function roleLabel(role: UserRole): string {
  return role.charAt(0).toUpperCase() + role.slice(1);
}
