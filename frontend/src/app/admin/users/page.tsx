"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EworksButton, EworksInput, EworksLabel, EworksLoadingScreen } from "@/components/eworks-ui";
import type { UserRole } from "@/lib/auth/types";
import {
  formatDate,
  getUser,
  listUsers,
  roleLabel,
  updateUser,
  USER_ROLES,
  type ManagedUser,
  type UserUpdatePayload,
} from "@/lib/users";

const PAGE_SIZE = 25;

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={
        active
          ? "inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800"
          : "inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700"
      }
    >
      {active ? "Active" : "Inactive"}
    </span>
  );
}

function RoleBadge({ role }: { role: UserRole }) {
  const styles: Record<UserRole, string> = {
    admin: "bg-purple-100 text-purple-800",
    manager: "bg-blue-100 text-blue-800",
    estimator: "bg-teal-100 text-teal-800",
    engineer: "bg-amber-100 text-amber-800",
    client: "bg-slate-100 text-slate-700",
  };
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${styles[role]}`}>
      {roleLabel(role)}
    </span>
  );
}

function UserEditPanel({
  user,
  onClose,
  onSaved,
}: {
  user: ManagedUser;
  onClose: () => void;
  onSaved: (user: ManagedUser) => void;
}) {
  const [name, setName] = useState(user.name || "");
  const [role, setRole] = useState<UserRole>(user.role);
  const [isActive, setIsActive] = useState(user.is_active);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    setSaving(true);
    setError(null);
    const payload: UserUpdatePayload = {
      name: name.trim(),
      role,
      is_active: isActive,
    };
    try {
      const updated = await updateUser(user.id, payload);
      onSaved(updated);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save user");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="user-edit-title"
      data-testid="user-edit-modal"
    >
      <div className="w-full max-w-2xl rounded-lg border border-gray-200 bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-gray-200 px-6 py-4">
          <div>
            <h2 id="user-edit-title" className="text-lg font-semibold text-gray-900">
              Edit User
            </h2>
            <p className="mt-1 text-sm text-gray-600">{user.email}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-900"
          >
            Close
          </button>
        </div>

        <div className="space-y-4 px-6 py-5">
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Azure login is not enabled yet. These roles will be reused when Azure users are mapped later.
          </p>

          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <EworksLabel>
            Name *
            <EworksInput value={name} onChange={(event) => setName(event.target.value)} data-testid="user-name-input" />
          </EworksLabel>

          <EworksLabel>
            Role
            <select
              value={role}
              onChange={(event) => setRole(event.target.value as UserRole)}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 shadow-sm focus:border-optimal-orange focus:outline-none focus:ring-2 focus:ring-optimal-orange/30"
              data-testid="user-role-select"
            >
              {USER_ROLES.map((option) => (
                <option key={option} value={option}>
                  {roleLabel(option)}
                </option>
              ))}
            </select>
          </EworksLabel>

          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(event) => setIsActive(event.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-optimal-orange"
              data-testid="user-active-checkbox"
            />
            Active account
          </label>

          <dl className="grid gap-3 rounded-lg bg-gray-50 p-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Email</dt>
              <dd className="mt-1 text-gray-900">{user.email}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">User ID</dt>
              <dd className="mt-1 break-all font-mono text-xs text-gray-900">{user.id}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Auth Provider</dt>
              <dd className="mt-1 text-gray-900">{user.auth_provider}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Created</dt>
              <dd className="mt-1 text-gray-900">{formatDate(user.created_at)}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Updated</dt>
              <dd className="mt-1 text-gray-900">{formatDate(user.updated_at)}</dd>
            </div>
          </dl>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-gray-200 px-6 py-4">
          <EworksButton type="button" variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </EworksButton>
          <EworksButton type="button" onClick={() => void handleSave()} disabled={saving} data-testid="user-save">
            {saving ? "Saving…" : "Save Changes"}
          </EworksButton>
        </div>
      </div>
    </div>
  );
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<UserRole | "">("");
  const [activeFilter, setActiveFilter] = useState<"all" | "active" | "inactive">("all");

  const [selectedUser, setSelectedUser] = useState<ManagedUser | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const filters = useMemo(
    () => ({
      search: search || undefined,
      role: roleFilter || undefined,
      active: activeFilter === "all" ? undefined : activeFilter === "active",
      limit: PAGE_SIZE,
      offset,
    }),
    [search, roleFilter, activeFilter, offset],
  );

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listUsers(filters);
      setUsers(result.items);
      setTotal(result.total);
    } catch (err) {
      setUsers([]);
      setTotal(0);
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  const applySearch = () => {
    setSearch(searchInput);
    setOffset(0);
  };

  const hasMore = offset + users.length < total;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const openEdit = async (userId: string) => {
    setDetailLoading(true);
    setError(null);
    try {
      const user = await getUser(userId);
      setSelectedUser(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load user details");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSaved = (updated: ManagedUser) => {
    setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
  };

  return (
    <div className="space-y-6" data-testid="admin-users-page">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Users & Roles</h1>
          <p className="mt-2 text-sm text-gray-600">
            Manage internal user accounts and role assignments. Azure identity mapping will be added in a later phase.
          </p>
        </div>
        <EworksButton type="button" variant="secondary" onClick={() => void loadUsers()} disabled={loading}>
          Refresh
        </EworksButton>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <EworksLabel>
            Search
            <EworksInput
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Name or email"
              data-testid="users-search"
            />
          </EworksLabel>
          <EworksLabel>
            Role
            <select
              value={roleFilter}
              onChange={(event) => {
                setRoleFilter(event.target.value as UserRole | "");
                setOffset(0);
              }}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 shadow-sm focus:border-optimal-orange focus:outline-none focus:ring-2 focus:ring-optimal-orange/30"
              data-testid="users-role-filter"
            >
              <option value="">All roles</option>
              {USER_ROLES.map((role) => (
                <option key={role} value={role}>
                  {roleLabel(role)}
                </option>
              ))}
            </select>
          </EworksLabel>
          <EworksLabel>
            Status
            <select
              value={activeFilter}
              onChange={(event) => {
                setActiveFilter(event.target.value as "all" | "active" | "inactive");
                setOffset(0);
              }}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 shadow-sm focus:border-optimal-orange focus:outline-none focus:ring-2 focus:ring-optimal-orange/30"
              data-testid="users-status-filter"
            >
              <option value="all">All statuses</option>
              <option value="active">Active only</option>
              <option value="inactive">Inactive only</option>
            </select>
          </EworksLabel>
          <div className="flex flex-col justify-end">
            <EworksButton type="button" onClick={applySearch}>
              Apply search
            </EworksButton>
          </div>
        </div>
      </div>

      {loading ? (
        <EworksLoadingScreen message="Loading users…" />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      ) : users.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
          <p className="text-sm text-gray-600">No users match your filters.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm" data-testid="users-table">
              <thead className="bg-gray-50">
                <tr>
                  {["Name", "Email", "Role", "Status", "Auth Provider", "Updated At", "Actions"].map((heading) => (
                    <th
                      key={heading}
                      scope="col"
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                    >
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {users.map((user) => (
                  <tr key={user.id} data-testid={`user-row-${user.id}`}>
                    <td className="px-4 py-3 font-medium text-gray-900">{user.name?.trim() || "—"}</td>
                    <td className="px-4 py-3 text-gray-700">{user.email}</td>
                    <td className="px-4 py-3">
                      <RoleBadge role={user.role} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge active={user.is_active} />
                    </td>
                    <td className="px-4 py-3 text-gray-700">{user.auth_provider}</td>
                    <td className="px-4 py-3 text-gray-700">{formatDate(user.updated_at)}</td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => void openEdit(user.id)}
                        className="text-sm font-medium text-gray-900 underline-offset-2 hover:underline"
                        data-testid={`user-edit-${user.id}`}
                      >
                        View / Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-200 px-4 py-3 text-sm text-gray-600">
            <p>
              Page {currentPage} of {lastPage} · {total} total
            </p>
            <div className="flex gap-2">
              <EworksButton
                type="button"
                variant="secondary"
                disabled={offset <= 0 || loading}
                onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
              >
                Previous
              </EworksButton>
              <EworksButton
                type="button"
                variant="secondary"
                disabled={!hasMore || loading}
                onClick={() => setOffset((current) => current + PAGE_SIZE)}
                data-testid="users-load-more"
              >
                Next
              </EworksButton>
            </div>
          </div>
        </div>
      )}

      {detailLoading && !selectedUser ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20">
          <EworksLoadingScreen message="Loading user…" />
        </div>
      ) : null}

      {selectedUser ? (
        <UserEditPanel user={selectedUser} onClose={() => setSelectedUser(null)} onSaved={handleSaved} />
      ) : null}
    </div>
  );
}
