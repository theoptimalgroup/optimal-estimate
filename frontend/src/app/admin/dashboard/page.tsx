"use client";

import Link from "next/link";
import {
  BarChart3,
  Calculator,
  ClipboardCheck,
  Package,
  Settings,
  Shield,
  Users,
  Wrench,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  DateText,
  ErrorState,
  LoadingState,
  PageHeader,
  SectionCard,
  StatCard,
  StatusBadge,
} from "@/components/ui";
import { listAuditLogs, type AuditLog } from "@/lib/audit-logs";
import { getSettings, getSettingsStatus, type SettingsStatus, type SystemSettings } from "@/lib/settings";

const quickLinks = [
  { href: "/new-estimate", label: "New Estimate", icon: Calculator },
  { href: "/manager/review", label: "Quote Review", icon: ClipboardCheck },
  { href: "/manager/reports", label: "Reports", icon: BarChart3 },
  { href: "/admin/users", label: "Users & Roles", icon: Users },
  { href: "/admin/clients", label: "Clients", icon: Wrench },
  { href: "/admin/trades", label: "Trades", icon: Wrench },
  { href: "/admin/products", label: "Products / Scope", icon: Package },
  { href: "/admin/rate-rules", label: "Rate Rules", icon: BarChart3 },
  { href: "/admin/audit-logs", label: "Audit Logs", icon: Shield },
  { href: "/admin/settings", label: "Settings", icon: Settings },
];

export default function AdminDashboardPage() {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [status, setStatus] = useState<SettingsStatus | null>(null);
  const [recentLogs, setRecentLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [settingsData, statusData, logsData] = await Promise.all([
        getSettings(),
        getSettingsStatus(),
        listAuditLogs({ limit: 5, offset: 0 }),
      ]);
      setSettings(settingsData);
      setStatus(statusData);
      setRecentLogs(logsData.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6" data-testid="admin-dashboard-page">
      <PageHeader
        title="Admin Dashboard"
        description="System overview, quick links, and recent activity."
      />

      {loading ? (
        <LoadingState message="Loading dashboard…" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void load()} />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Users" value={status?.counts.users ?? 0} />
            <StatCard label="Products" value={status?.counts.products ?? 0} />
            <StatCard label="Submitted quotes" value={status?.counts.submitted_sessions ?? 0} />
            <StatCard label="Audit logs" value={status?.counts.audit_logs ?? 0} />
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <SectionCard title="Quick links" className="lg:col-span-1">
              <ul className="grid gap-2">
                {quickLinks.map((link) => {
                  const Icon = link.icon;
                  return (
                    <li key={link.href}>
                      <Link
                        href={link.href}
                        className="flex items-center gap-3 rounded-lg border border-slate-100 px-3 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
                      >
                        <Icon className="size-4 text-slate-400" />
                        {link.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </SectionCard>

            <SectionCard title="System status" className="lg:col-span-1">
              <dl className="space-y-3 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-slate-600">Database</dt>
                  <dd>
                    <StatusBadge tone={status?.database_reachable ? "success" : "error"}>
                      {status?.database_reachable ? "Reachable" : "Unavailable"}
                    </StatusBadge>
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-slate-600">Auth provider</dt>
                  <dd className="font-medium capitalize text-slate-900">{settings?.auth.auth_provider ?? "—"}</dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-slate-600">Environment</dt>
                  <dd className="font-medium text-slate-900">{settings?.app.environment ?? "—"}</dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-slate-600">eWorks API</dt>
                  <dd>
                    <StatusBadge tone={settings?.eworks.api_enabled ? "success" : "neutral"}>
                      {settings?.eworks.api_enabled ? "Enabled" : "Disabled"}
                    </StatusBadge>
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-slate-600">PDF generation</dt>
                  <dd>
                    <StatusBadge tone={settings?.pdf.enabled ? "success" : "neutral"}>
                      {settings?.pdf.enabled ? "Enabled" : "Disabled"}
                    </StatusBadge>
                  </dd>
                </div>
              </dl>
            </SectionCard>

            <SectionCard
              title="Recent audit logs"
              actions={
                <Link href="/admin/audit-logs" className="text-sm font-medium text-blue-600 hover:text-blue-700">
                  View all
                </Link>
              }
              className="lg:col-span-1"
            >
              {recentLogs.length === 0 ? (
                <p className="text-sm text-slate-500">No audit activity yet.</p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {recentLogs.map((log) => (
                    <li key={log.id} className="py-3 first:pt-0 last:pb-0">
                      <p className="text-sm font-medium text-slate-900">{log.summary}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {log.actor_email ?? "System"} · <DateText value={log.created_at} includeTime />
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </SectionCard>
          </div>
        </>
      )}
    </div>
  );
}
