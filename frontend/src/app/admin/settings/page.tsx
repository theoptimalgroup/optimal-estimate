"use client";

import { useCallback, useEffect, useState } from "react";

import { EworksButton, EworksLoadingScreen } from "@/components/eworks-ui";
import {
  formatProviderLabel,
  formatSettingsDate,
  getSettings,
  getSettingsStatus,
  type SettingsStatus,
  type SystemSettings,
} from "@/lib/settings";

function StatusBadge({ ok, label }: { ok: boolean; label?: string }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
        ok ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
      }`}
      data-testid={label ? `status-badge-${label}` : undefined}
    >
      {ok ? "Configured" : "Not configured"}
    </span>
  );
}

function BoolBadge({ value, trueLabel = "Yes", falseLabel = "No" }: { value: boolean; trueLabel?: string; falseLabel?: string }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
        value ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700"
      }`}
    >
      {value ? trueLabel : falseLabel}
    </span>
  );
}

function SettingsCard({ title, children, testId }: { title: string; children: React.ReactNode; testId: string }) {
  return (
    <section className="rounded-lg border border-gray-200 bg-white shadow-sm" data-testid={testId}>
      <div className="border-b border-gray-200 px-5 py-4">
        <h2 className="text-base font-semibold text-gray-900">{title}</h2>
      </div>
      <dl className="divide-y divide-gray-100 px-5 py-2">{children}</dl>
    </section>
  );
}

function SettingsRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid gap-1 py-3 sm:grid-cols-2 sm:gap-4">
      <dt className="text-sm font-medium text-gray-500">{label}</dt>
      <dd className="text-sm text-gray-900">{value}</dd>
    </div>
  );
}

function HiddenValue({ configured }: { configured: boolean }) {
  if (!configured) {
    return <span className="text-gray-500">Not configured</span>;
  }
  return (
    <span className="font-mono text-xs text-gray-600" data-testid="redacted-value">
      Configured, value hidden (***REDACTED***)
    </span>
  );
}

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [status, setStatus] = useState<SettingsStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [settingsData, statusData] = await Promise.all([getSettings(), getSettingsStatus()]);
      setSettings(settingsData);
      setStatus(statusData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
      setSettings(null);
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  return (
    <div className="space-y-6" data-testid="admin-settings-page">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Settings</h1>
          <p className="mt-2 text-sm text-gray-600">System configuration and operational status</p>
        </div>
        <EworksButton type="button" onClick={() => void loadSettings()} disabled={loading}>
          Refresh
        </EworksButton>
      </div>

      {loading ? (
        <EworksLoadingScreen message="Loading settings…" />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" data-testid="settings-error">
          {error}
        </div>
      ) : settings ? (
        <div className="grid gap-6 xl:grid-cols-2">
          <SettingsCard title="App / Environment" testId="settings-app-card">
            <SettingsRow label="Environment" value={settings.app.environment} />
            <SettingsRow label="Debug mode" value={<BoolBadge value={settings.app.debug} trueLabel="Enabled" falseLabel="Disabled" />} />
            <SettingsRow label="API version" value={settings.app.version || "—"} />
            <SettingsRow label="API prefix" value={settings.app.api_prefix} />
            <SettingsRow label="Formula version" value={settings.app.formula_version} />
            <SettingsRow label="Template version" value={settings.app.template_version} />
          </SettingsCard>

          <SettingsCard title="Auth" testId="settings-auth-card">
            <SettingsRow label="Auth provider" value={settings.auth.auth_provider} />
            <SettingsRow label="Dev auth enabled" value={<BoolBadge value={settings.auth.dev_auth_enabled} />} />
            <SettingsRow label="Dev auth email" value={settings.auth.dev_auth_email || "—"} />
            <SettingsRow label="Auto-create user" value={<BoolBadge value={settings.auth.dev_auth_auto_create_user} />} />
            <SettingsRow
              label="Azure enabled"
              value={<span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">Coming later</span>}
            />
          </SettingsCard>

          <SettingsCard title="eWorks Integration" testId="settings-eworks-card">
            <SettingsRow
              label="Base URL"
              value={<StatusBadge ok={settings.eworks.base_url_configured} label="eworks-base-url" />}
            />
            <SettingsRow
              label="API key"
              value={<StatusBadge ok={settings.eworks.api_key_configured} label="eworks-api-key" />}
            />
            <SettingsRow
              label="License key"
              value={<StatusBadge ok={settings.eworks.license_key_configured} label="eworks-license-key" />}
            />
            <SettingsRow label="API enabled" value={<BoolBadge value={settings.eworks.api_enabled} />} />
            <SettingsRow
              label="Acceptance sync enabled"
              value={<BoolBadge value={settings.eworks.acceptance_sync.enabled} />}
            />
            <SettingsRow label="Acceptance sync mode" value={settings.eworks.acceptance_sync.mode || "—"} />
            <SettingsRow
              label="Custom field configured"
              value={<BoolBadge value={settings.eworks.acceptance_sync.custom_field_configured} />}
            />
            <SettingsRow
              label="Custom field ID"
              value={String(settings.eworks.acceptance_sync.custom_field_id ?? "—")}
            />
            <SettingsRow
              label="Custom field key"
              value={settings.eworks.acceptance_sync.custom_field_key || "—"}
            />
          </SettingsCard>

          <SettingsCard title="Dashboard" testId="settings-dashboard-card">
            <SettingsRow
              label="Dashboard password"
              value={
                <div className="space-y-1">
                  <StatusBadge ok={settings.dashboard.password_configured} label="dashboard-password" />
                  <HiddenValue configured={settings.dashboard.password_configured} />
                </div>
              }
            />
          </SettingsCard>

          <SettingsCard title="Storage / PDF" testId="settings-storage-card">
            <SettingsRow label="Storage provider" value={formatProviderLabel(settings.storage.provider)} />
            <SettingsRow
              label="Azure Blob"
              value={<StatusBadge ok={settings.storage.azure_blob_configured} label="azure-blob" />}
            />
            <SettingsRow label="PDF enabled" value={<BoolBadge value={settings.pdf.enabled} />} />
            <SettingsRow label="PDF engine" value={settings.pdf.engine || "—"} />
          </SettingsCard>

          <SettingsCard title="Database / Security" testId="settings-database-card">
            <SettingsRow
              label="Database"
              value={
                <div className="space-y-1">
                  <StatusBadge ok={settings.database.configured} label="database" />
                  <HiddenValue configured={settings.database.configured} />
                </div>
              }
            />
            <SettingsRow label="CORS origins count" value={settings.security.cors_origins_count} />
            <SettingsRow
              label="Allowed hosts count"
              value={settings.security.allowed_hosts_count ?? "Not configured"}
            />
          </SettingsCard>

          {status ? (
            <SettingsCard title="Operational Status" testId="settings-status-card">
              <SettingsRow
                label="Database reachable"
                value={<BoolBadge value={status.database_reachable} trueLabel="Reachable" falseLabel="Unreachable" />}
              />
              <SettingsRow label="Users" value={status.counts.users} />
              <SettingsRow label="Clients" value={status.counts.clients} />
              <SettingsRow label="Trades" value={status.counts.trades} />
              <SettingsRow label="Products" value={status.counts.products} />
              <SettingsRow label="Rate rules" value={status.counts.rate_rules} />
              <SettingsRow label="Submitted sessions" value={status.counts.submitted_sessions} />
              <SettingsRow label="Audit logs" value={status.counts.audit_logs} />
              <SettingsRow label="Last product sync" value={formatSettingsDate(status.last_product_sync_at)} />
              <SettingsRow label="Latest audit log" value={formatSettingsDate(status.latest_audit_log_at)} />
            </SettingsCard>
          ) : null}
        </div>
      ) : (
        <p className="text-sm text-gray-500">No settings data available.</p>
      )}
    </div>
  );
}
