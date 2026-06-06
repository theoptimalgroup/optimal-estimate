"use client";

import { useCallback, useEffect, useState } from "react";

import {
  DateText,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  PrimaryButton,
  SectionCard,
  StatusBadge,
} from "@/components/ui";
import {
  formatProviderLabel,
  getSettings,
  getSettingsStatus,
  type SettingsStatus,
  type SystemSettings,
} from "@/lib/settings";

function ConfigStatusBadge({ ok, label }: { ok: boolean; label?: string }) {
  return (
    <StatusBadge
      tone={ok ? "success" : "error"}
      data-testid={label ? `status-badge-${label}` : undefined}
    >
      {ok ? "Configured" : "Not configured"}
    </StatusBadge>
  );
}

function BoolBadge({ value, trueLabel = "Yes", falseLabel = "No" }: { value: boolean; trueLabel?: string; falseLabel?: string }) {
  return (
    <StatusBadge tone={value ? "success" : "neutral"}>
      {value ? trueLabel : falseLabel}
    </StatusBadge>
  );
}

function SettingsRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid gap-1 py-3 sm:grid-cols-2 sm:gap-4">
      <dt className="text-sm font-medium text-slate-500">{label}</dt>
      <dd className="text-sm text-slate-900">{value}</dd>
    </div>
  );
}

function HiddenValue({ configured }: { configured: boolean }) {
  if (!configured) {
    return <span className="text-slate-500">Not configured</span>;
  }
  return (
    <span className="font-mono text-xs text-slate-600" data-testid="redacted-value">
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
      <PageHeader
        title="Settings"
        description="System configuration and operational status"
        actions={
          <PrimaryButton onClick={() => void loadSettings()} disabled={loading}>
            Refresh
          </PrimaryButton>
        }
      />

      {loading ? (
        <LoadingState message="Loading settings…" />
      ) : error ? (
        <div data-testid="settings-error">
          <ErrorState message={error} />
        </div>
      ) : settings ? (
        <div className="grid gap-6 xl:grid-cols-2">
          <SectionCard title="App / Environment" testId="settings-app-card">
            <dl className="divide-y divide-slate-100">
              <SettingsRow label="Environment" value={settings.app.environment} />
              <SettingsRow
                label="Debug mode"
                value={<BoolBadge value={settings.app.debug} trueLabel="Enabled" falseLabel="Disabled" />}
              />
              <SettingsRow label="API version" value={settings.app.version || "—"} />
              <SettingsRow label="API prefix" value={settings.app.api_prefix} />
              <SettingsRow label="Formula version" value={settings.app.formula_version} />
              <SettingsRow label="Template version" value={settings.app.template_version} />
            </dl>
          </SectionCard>

          <SectionCard title="Auth" testId="settings-auth-card">
            <dl className="divide-y divide-slate-100">
              <SettingsRow label="Auth provider" value={settings.auth.auth_provider} />
              <SettingsRow label="Dev auth enabled" value={<BoolBadge value={settings.auth.dev_auth_enabled} />} />
              <SettingsRow label="Dev auth email" value={settings.auth.dev_auth_email || "—"} />
              <SettingsRow label="Auto-create user" value={<BoolBadge value={settings.auth.dev_auth_auto_create_user} />} />
              <SettingsRow
                label="Azure enabled"
                value={<StatusBadge tone="neutral">Coming later</StatusBadge>}
              />
            </dl>
          </SectionCard>

          <SectionCard title="eWorks Integration" testId="settings-eworks-card">
            <dl className="divide-y divide-slate-100">
              <SettingsRow
                label="Base URL"
                value={<ConfigStatusBadge ok={settings.eworks.base_url_configured} label="eworks-base-url" />}
              />
              <SettingsRow
                label="API key"
                value={<ConfigStatusBadge ok={settings.eworks.api_key_configured} label="eworks-api-key" />}
              />
              <SettingsRow
                label="License key"
                value={<ConfigStatusBadge ok={settings.eworks.license_key_configured} label="eworks-license-key" />}
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
            </dl>
          </SectionCard>

          <SectionCard title="Background eWorks Sync" testId="settings-background-sync-card">
            <dl className="divide-y divide-slate-100">
              <SettingsRow
                label="Background sync enabled"
                value={<BoolBadge value={settings.eworks.background_sync.enabled} />}
              />
              <SettingsRow
                label="Background worker"
                value={<BoolBadge value={settings.eworks.background_sync.worker_enabled} />}
              />
              <SettingsRow
                label="Scheduler active"
                value={<BoolBadge value={settings.eworks.background_sync.scheduler_active} />}
              />
              <SettingsRow
                label="Quotes interval"
                value={`Every ${settings.eworks.background_sync.quotes_interval_minutes} minutes`}
              />
              <SettingsRow
                label="Jobs interval"
                value={`Every ${settings.eworks.background_sync.jobs_interval_minutes} minutes`}
              />
              <SettingsRow
                label="Products interval"
                value={`Every ${settings.eworks.background_sync.products_interval_minutes} minutes`}
              />
              <SettingsRow
                label="Lookback days"
                value={String(settings.eworks.background_sync.lookback_days)}
              />
              <SettingsRow
                label="Running timeout"
                value={`${settings.eworks.background_sync.running_timeout_minutes} minutes`}
              />
            </dl>
            <p className="mt-4 text-xs text-slate-500">
              Values are read from environment configuration. Editing from the UI is not supported yet.
            </p>
          </SectionCard>

          <SectionCard title="Dashboard" testId="settings-dashboard-card">
            <dl className="divide-y divide-slate-100">
              <SettingsRow
                label="Dashboard password"
                value={
                  <div className="space-y-1">
                    <ConfigStatusBadge ok={settings.dashboard.password_configured} label="dashboard-password" />
                    <HiddenValue configured={settings.dashboard.password_configured} />
                  </div>
                }
              />
            </dl>
          </SectionCard>

          <SectionCard title="Storage / PDF" testId="settings-storage-card">
            <dl className="divide-y divide-slate-100">
              <SettingsRow label="Storage provider" value={formatProviderLabel(settings.storage.provider)} />
              <SettingsRow
                label="Azure Blob"
                value={<ConfigStatusBadge ok={settings.storage.azure_blob_configured} label="azure-blob" />}
              />
              <SettingsRow label="PDF enabled" value={<BoolBadge value={settings.pdf.enabled} />} />
              <SettingsRow label="PDF engine" value={settings.pdf.engine || "—"} />
            </dl>
          </SectionCard>

          <SectionCard title="Database / Security" testId="settings-database-card">
            <dl className="divide-y divide-slate-100">
              <SettingsRow
                label="Database"
                value={
                  <div className="space-y-1">
                    <ConfigStatusBadge ok={settings.database.configured} label="database" />
                    <HiddenValue configured={settings.database.configured} />
                  </div>
                }
              />
              <SettingsRow label="CORS origins count" value={settings.security.cors_origins_count} />
              <SettingsRow
                label="Allowed hosts count"
                value={settings.security.allowed_hosts_count ?? "Not configured"}
              />
            </dl>
          </SectionCard>

          {status ? (
            <SectionCard title="Operational Status" testId="settings-status-card">
              <dl className="divide-y divide-slate-100">
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
                <SettingsRow
                  label="Last product sync"
                  value={<DateText value={status.last_product_sync_at} includeTime />}
                />
                <SettingsRow
                  label="Latest audit log"
                  value={<DateText value={status.latest_audit_log_at} includeTime />}
                />
              </dl>
            </SectionCard>
          ) : null}
        </div>
      ) : (
        <EmptyState title="No settings data" description="No settings data available." />
      )}
    </div>
  );
}
