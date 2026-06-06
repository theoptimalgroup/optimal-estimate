"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EworksInput, EworksLabel } from "@/components/eworks-ui";
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableRow,
  DateText,
  EmptyState,
  ErrorState,
  FilterBar,
  FilterField,
  LoadingState,
  PageHeader,
  PrimaryButton,
  RoleBadge,
  SecondaryButton,
  SectionCard,
  StatusBadge,
  activeStatusTone,
  filterInputClass,
  filterSelectClass,
} from "@/components/ui";
import type { UserRole } from "@/lib/auth/types";
import {
  formatDate,
  createUser,
  getUser,
  listUsers,
  roleLabel,
  updateUser,
  USER_ROLES,
  type ManagedUser,
  type UserCreatePayload,
  type UserUpdatePayload,
} from "@/lib/users";

const PAGE_SIZE = 25;

function UserCreatePanel({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (user: ManagedUser) => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<UserRole>("estimator");
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    if (!email.trim()) {
      setError("Email is required");
      return;
    }
    setSaving(true);
    setError(null);
    const payload: UserCreatePayload = {
      email: email.trim(),
      name: name.trim(),
      role,
      is_active: isActive,
    };
    try {
      const created = await createUser(payload);
      onCreated(created);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="user-create-title"
      data-testid="user-create-modal"
    >
      <div className="w-full max-w-2xl rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
          <div>
            <h2 id="user-create-title" className="text-lg font-semibold text-slate-900">
              Add User
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Pre-register a user for Azure sign-in. Email must match their Azure account.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2.5 py-1.5 text-sm text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
          >
            Close
          </button>
        </div>

        <div className="space-y-5 px-6 py-6">
          {error ? <p className="text-sm text-rose-600" data-testid="user-create-error">{error}</p> : null}

          <EworksLabel>
            Name *
            <EworksInput
              value={name}
              onChange={(event) => setName(event.target.value)}
              data-testid="user-create-name-input"
            />
          </EworksLabel>

          <EworksLabel>
            Email *
            <EworksInput
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              data-testid="user-create-email-input"
            />
          </EworksLabel>

          <EworksLabel>
            Role *
            <select
              value={role}
              onChange={(event) => setRole(event.target.value as UserRole)}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              data-testid="user-create-role-select"
            >
              {USER_ROLES.map((option) => (
                <option key={option} value={option}>
                  {roleLabel(option)}
                </option>
              ))}
            </select>
          </EworksLabel>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(event) => setIsActive(event.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              data-testid="user-create-active-checkbox"
            />
            Active account
          </label>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-slate-100 px-6 py-5">
          <SecondaryButton onClick={onClose} disabled={saving}>
            Cancel
          </SecondaryButton>
          <PrimaryButton onClick={() => void handleSave()} disabled={saving} data-testid="user-create-save">
            {saving ? "Creating…" : "Create User"}
          </PrimaryButton>
        </div>
      </div>
    </div>
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
      <div className="w-full max-w-2xl rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
          <div>
            <h2 id="user-edit-title" className="text-lg font-semibold text-slate-900">
              Edit User
            </h2>
            <p className="mt-1 text-sm text-slate-600">{user.email}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2.5 py-1.5 text-sm text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
          >
            Close
          </button>
        </div>

        <div className="space-y-5 px-6 py-6">
          <p className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
            Users sign in with Azure. Email must match their Azure account for role mapping.
          </p>

          {error ? <p className="text-sm text-rose-600">{error}</p> : null}

          <EworksLabel>
            Name *
            <EworksInput value={name} onChange={(event) => setName(event.target.value)} data-testid="user-name-input" />
          </EworksLabel>

          <EworksLabel>
            Role
            <select
              value={role}
              onChange={(event) => setRole(event.target.value as UserRole)}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              data-testid="user-role-select"
            >
              {USER_ROLES.map((option) => (
                <option key={option} value={option}>
                  {roleLabel(option)}
                </option>
              ))}
            </select>
          </EworksLabel>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(event) => setIsActive(event.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              data-testid="user-active-checkbox"
            />
            Active account
          </label>

          <dl className="grid gap-3 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Email</dt>
              <dd className="mt-1 text-slate-900">{user.email}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">User ID</dt>
              <dd className="mt-1 break-all font-mono text-xs text-slate-900">{user.id}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Auth Provider</dt>
              <dd className="mt-1 text-slate-900">{user.auth_provider}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Created</dt>
              <dd className="mt-1 text-slate-900">{formatDate(user.created_at)}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Updated</dt>
              <dd className="mt-1 text-slate-900">{formatDate(user.updated_at)}</dd>
            </div>
          </dl>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-slate-100 px-6 py-5">
          <SecondaryButton onClick={onClose} disabled={saving}>
            Cancel
          </SecondaryButton>
          <PrimaryButton onClick={() => void handleSave()} disabled={saving} data-testid="user-save">
            {saving ? "Saving…" : "Save Changes"}
          </PrimaryButton>
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
  const [createOpen, setCreateOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
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

  const handleCreated = (created: ManagedUser) => {
    setSuccessMessage(`User ${created.email} created successfully.`);
    void loadUsers();
  };

  return (
    <div className="space-y-6" data-testid="admin-users-page">
      <PageHeader
        title="Users & Roles"
        description="Manage user accounts and role assignments for Azure sign-in mapping."
        actions={
          <>
            <PrimaryButton onClick={() => setCreateOpen(true)} data-testid="btn-add-user">
              Add User
            </PrimaryButton>
            <SecondaryButton onClick={() => void loadUsers()} disabled={loading}>
              Refresh
            </SecondaryButton>
          </>
        }
      />

      {successMessage ? (
        <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900" data-testid="user-create-success">
          {successMessage}
        </p>
      ) : null}

      <FilterBar>
        <FilterField label="Search">
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Name or email"
            className={filterInputClass}
            data-testid="users-search"
          />
        </FilterField>
        <FilterField label="Role">
          <select
            value={roleFilter}
            onChange={(event) => {
              setRoleFilter(event.target.value as UserRole | "");
              setOffset(0);
            }}
            className={filterSelectClass}
            data-testid="users-role-filter"
          >
            <option value="">All roles</option>
            {USER_ROLES.map((role) => (
              <option key={role} value={role}>
                {roleLabel(role)}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Status">
          <select
            value={activeFilter}
            onChange={(event) => {
              setActiveFilter(event.target.value as "all" | "active" | "inactive");
              setOffset(0);
            }}
            className={filterSelectClass}
            data-testid="users-status-filter"
          >
            <option value="all">All statuses</option>
            <option value="active">Active only</option>
            <option value="inactive">Inactive only</option>
          </select>
        </FilterField>
        <div className="flex shrink-0 items-end">
          <PrimaryButton onClick={applySearch}>Apply search</PrimaryButton>
        </div>
      </FilterBar>

      {loading ? (
        <LoadingState message="Loading users…" />
      ) : error ? (
        <ErrorState message={error} />
      ) : users.length === 0 ? (
        <EmptyState title="No users found" description="No users match your filters." />
      ) : (
        <SectionCard padding="none">
          <DataTable testId="users-table" className="rounded-none border-0 shadow-none">
            <DataTableHead>
              {["Name", "Email", "Role", "Status", "Auth Provider", "Updated At", "Actions"].map((heading) => (
                <DataTableCell key={heading} header>
                  {heading}
                </DataTableCell>
              ))}
            </DataTableHead>
            <DataTableBody>
              {users.map((user) => (
                <DataTableRow key={user.id} data-testid={`user-row-${user.id}`}>
                  <DataTableCell className="font-medium text-slate-900">{user.name?.trim() || "—"}</DataTableCell>
                  <DataTableCell>{user.email}</DataTableCell>
                  <DataTableCell>
                    <RoleBadge role={user.role} />
                  </DataTableCell>
                  <DataTableCell>
                    <StatusBadge tone={activeStatusTone(user.is_active)}>
                      {user.is_active ? "Active" : "Inactive"}
                    </StatusBadge>
                  </DataTableCell>
                  <DataTableCell>{user.auth_provider}</DataTableCell>
                  <DataTableCell>
                    <DateText value={user.updated_at} includeTime />
                  </DataTableCell>
                  <DataTableCell>
                    <button
                      type="button"
                      onClick={() => void openEdit(user.id)}
                      className="text-sm font-medium text-blue-600 underline-offset-2 hover:text-blue-700 hover:underline"
                      data-testid={`user-edit-${user.id}`}
                    >
                      View / Edit
                    </button>
                  </DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
            <p>
              Page {currentPage} of {lastPage} · {total} total
            </p>
            <div className="flex gap-2">
              <SecondaryButton
                disabled={offset <= 0 || loading}
                onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
              >
                Previous
              </SecondaryButton>
              <SecondaryButton
                disabled={!hasMore || loading}
                onClick={() => setOffset((current) => current + PAGE_SIZE)}
                data-testid="users-load-more"
              >
                Next
              </SecondaryButton>
            </div>
          </div>
        </SectionCard>
      )}

      {detailLoading && !selectedUser ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20">
          <LoadingState message="Loading user…" />
        </div>
      ) : null}

      {selectedUser ? (
        <UserEditPanel user={selectedUser} onClose={() => setSelectedUser(null)} onSaved={handleSaved} />
      ) : null}

      {createOpen ? (
        <UserCreatePanel
          onClose={() => setCreateOpen(false)}
          onCreated={(user) => {
            handleCreated(user);
            setCreateOpen(false);
          }}
        />
      ) : null}
    </div>
  );
}
