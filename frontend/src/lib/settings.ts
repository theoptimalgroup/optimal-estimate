import { apiFetch } from "@/lib/api";

export type AppSettings = {
  environment: string;
  debug: boolean;
  version: string;
  api_prefix: string;
  formula_version: string;
  template_version: string;
};

export type AuthSettings = {
  dev_auth_enabled: boolean;
  dev_auth_email: string;
  dev_auth_auto_create_user: boolean;
  azure_enabled: boolean;
  auth_provider: string;
};

export type EworksAcceptanceSyncSettings = {
  enabled: boolean;
  mode: string;
  custom_field_id: number;
  custom_field_key: string;
  custom_field_configured: boolean;
};

export type EworksBackgroundSyncSettings = {
  enabled: boolean;
  worker_enabled: boolean;
  scheduler_active: boolean;
  quotes_enabled: boolean;
  jobs_enabled: boolean;
  products_enabled: boolean;
  attachments_enabled: boolean;
  quotes_interval_minutes: number;
  jobs_interval_minutes: number;
  products_interval_minutes: number;
  lookback_days: number;
  running_timeout_minutes: number;
};

export type EworksSettings = {
  base_url_configured: boolean;
  api_key_configured: boolean;
  license_key_configured: boolean;
  api_enabled: boolean;
  acceptance_sync: EworksAcceptanceSyncSettings;
  background_sync: EworksBackgroundSyncSettings;
};

export type DashboardSettings = {
  password_configured: boolean;
  password_value: string;
};

export type StorageSettings = {
  provider: string;
  azure_blob_configured: boolean;
};

export type PdfSettings = {
  enabled: boolean;
  engine: string;
};

export type DatabaseSettings = {
  configured: boolean;
  url: string;
};

export type SecuritySettings = {
  cors_origins_count: number;
  allowed_hosts_count: number | null;
};

export type SystemSettings = {
  app: AppSettings;
  auth: AuthSettings;
  eworks: EworksSettings;
  dashboard: DashboardSettings;
  storage: StorageSettings;
  pdf: PdfSettings;
  database: DatabaseSettings;
  security: SecuritySettings;
};

export type SettingsCounts = {
  users: number;
  clients: number;
  trades: number;
  products: number;
  rate_rules: number;
  submitted_sessions: number;
  audit_logs: number;
};

export type SettingsStatus = {
  database_reachable: boolean;
  counts: SettingsCounts;
  last_product_sync_at: string | null;
  latest_audit_log_at: string | null;
};

function normalizeSettings(raw: Record<string, unknown>): SystemSettings {
  const section = (key: string) => (raw[key] ?? {}) as Record<string, unknown>;

  const app = section("app");
  const auth = section("auth");
  const eworks = section("eworks");
  const backgroundSync = (eworks.background_sync ?? {}) as Record<string, unknown>;
  const dashboard = section("dashboard");
  const storage = section("storage");
  const pdf = section("pdf");
  const database = section("database");
  const security = section("security");

  return {
    app: {
      environment: String(app.environment ?? ""),
      debug: Boolean(app.debug),
      version: String(app.version ?? ""),
      api_prefix: String(app.api_prefix ?? ""),
      formula_version: String(app.formula_version ?? ""),
      template_version: String(app.template_version ?? ""),
    },
    auth: {
      dev_auth_enabled: Boolean(auth.dev_auth_enabled),
      dev_auth_email: String(auth.dev_auth_email ?? ""),
      dev_auth_auto_create_user: Boolean(auth.dev_auth_auto_create_user),
      azure_enabled: Boolean(auth.azure_enabled),
      auth_provider: String(auth.auth_provider ?? ""),
    },
    eworks: {
      base_url_configured: Boolean(eworks.base_url_configured),
      api_key_configured: Boolean(eworks.api_key_configured),
      license_key_configured: Boolean(eworks.license_key_configured),
      api_enabled: Boolean(eworks.api_enabled),
      acceptance_sync: {
        enabled: Boolean((eworks.acceptance_sync as Record<string, unknown> | undefined)?.enabled),
        mode: String((eworks.acceptance_sync as Record<string, unknown> | undefined)?.mode ?? "custom_field"),
        custom_field_id: Number((eworks.acceptance_sync as Record<string, unknown> | undefined)?.custom_field_id ?? 45),
        custom_field_key: String(
          (eworks.acceptance_sync as Record<string, unknown> | undefined)?.custom_field_key ?? "txtar_45",
        ),
        custom_field_configured: Boolean(
          (eworks.acceptance_sync as Record<string, unknown> | undefined)?.custom_field_configured,
        ),
      },
      background_sync: {
        enabled: Boolean(backgroundSync.enabled),
        worker_enabled: Boolean(backgroundSync.worker_enabled),
        scheduler_active: Boolean(backgroundSync.scheduler_active),
        quotes_enabled: Boolean(backgroundSync.quotes_enabled ?? true),
        jobs_enabled: Boolean(backgroundSync.jobs_enabled ?? true),
        products_enabled: Boolean(backgroundSync.products_enabled),
        attachments_enabled: Boolean(backgroundSync.attachments_enabled ?? true),
        quotes_interval_minutes: Number(backgroundSync.quotes_interval_minutes ?? 10),
        jobs_interval_minutes: Number(backgroundSync.jobs_interval_minutes ?? 30),
        products_interval_minutes: Number(backgroundSync.products_interval_minutes ?? 1440),
        lookback_days: Number(backgroundSync.lookback_days ?? 7),
        running_timeout_minutes: Number(backgroundSync.running_timeout_minutes ?? 30),
      },
    },
    dashboard: {
      password_configured: Boolean(dashboard.password_configured),
      password_value: String(dashboard.password_value ?? "***REDACTED***"),
    },
    storage: {
      provider: String(storage.provider ?? "unknown"),
      azure_blob_configured: Boolean(storage.azure_blob_configured),
    },
    pdf: {
      enabled: Boolean(pdf.enabled),
      engine: String(pdf.engine ?? ""),
    },
    database: {
      configured: Boolean(database.configured),
      url: String(database.url ?? "***REDACTED***"),
    },
    security: {
      cors_origins_count: Number(security.cors_origins_count ?? 0),
      allowed_hosts_count:
        security.allowed_hosts_count != null ? Number(security.allowed_hosts_count) : null,
    },
  };
}

function normalizeStatus(raw: Record<string, unknown>): SettingsStatus {
  const countsRaw = (raw.counts ?? {}) as Record<string, unknown>;
  return {
    database_reachable: Boolean(raw.database_reachable),
    counts: {
      users: Number(countsRaw.users ?? 0),
      clients: Number(countsRaw.clients ?? 0),
      trades: Number(countsRaw.trades ?? 0),
      products: Number(countsRaw.products ?? 0),
      rate_rules: Number(countsRaw.rate_rules ?? 0),
      submitted_sessions: Number(countsRaw.submitted_sessions ?? 0),
      audit_logs: Number(countsRaw.audit_logs ?? 0),
    },
    last_product_sync_at: raw.last_product_sync_at != null ? String(raw.last_product_sync_at) : null,
    latest_audit_log_at: raw.latest_audit_log_at != null ? String(raw.latest_audit_log_at) : null,
  };
}

export async function getSettings(): Promise<SystemSettings> {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/settings");
  return normalizeSettings((response.data ?? {}) as Record<string, unknown>);
}

export async function getSettingsStatus(): Promise<SettingsStatus> {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/settings/status");
  return normalizeStatus((response.data ?? {}) as Record<string, unknown>);
}

export function formatSettingsDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function formatProviderLabel(provider: string): string {
  if (provider === "local") return "Local filesystem";
  if (provider === "azure_blob") return "Azure Blob Storage";
  return provider || "Unknown";
}
