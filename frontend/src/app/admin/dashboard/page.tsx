"use client";

import Link from "next/link";
import {
  BarChart3,
  Calculator,
  Package,
  Settings,
  Shield,
  Users,
  Wrench,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { DashboardSearch } from "@/components/dashboard/dashboard-search";
import { QuoteBucketBoard } from "@/components/dashboard/quote-bucket-board";
import { QuoteDetailModal } from "@/components/manager/sync-detail-modals";
import {
  DateText,
  ErrorState,
  LoadingState,
  PageHeader,
  SectionCard,
  StatCard,
  StatusBadge,
} from "@/components/ui";
import {
  AWAITING_SUPPLIER_TAG,
  READY_TO_SEND_TAG,
  buildAdminQuotesFilterUrl,
  fetchAdminDashboard,
  type AdminDashboard,
} from "@/lib/admin-dashboard";
import {
  getSafeQuoteDetail,
  listQuoteAttachments,
  type EworksAttachmentSafe,
  type EworksQuoteSafeDetail,
} from "@/lib/eworks-sync";

const adminToolLinks = [
  { href: "/new-estimate", label: "New Estimate", icon: Calculator },
  { href: "/admin/users", label: "Users & Roles", icon: Users },
  { href: "/admin/clients", label: "Clients", icon: Wrench },
  { href: "/admin/trades", label: "Trades", icon: Wrench },
  { href: "/admin/products", label: "Products / Scope", icon: Package },
  { href: "/admin/rate-rules", label: "Rate Rules", icon: BarChart3 },
  { href: "/admin/audit-logs", label: "Audit Logs", icon: Shield },
  { href: "/admin/settings", label: "Settings", icon: Settings },
  { href: "/admin/eworks-sync", label: "eWorks Sync", icon: Settings },
];

export default function AdminDashboardPage() {
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  const [selectedQuoteId, setSelectedQuoteId] = useState<number | null>(null);
  const [quoteDetail, setQuoteDetail] = useState<EworksQuoteSafeDetail | null>(null);
  const [quoteDetailLoading, setQuoteDetailLoading] = useState(false);
  const [quoteDetailError, setQuoteDetailError] = useState<string | null>(null);
  const [quoteAttachments, setQuoteAttachments] = useState<EworksAttachmentSafe[]>([]);
  const [quoteAttachmentsLoading, setQuoteAttachmentsLoading] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAdminDashboard(10, debouncedSearch || undefined);
      setDashboard(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch]);

  useEffect(() => {
    void load();
  }, [load]);

  const openQuoteDetail = useCallback(async (id: number) => {
    setSelectedQuoteId(id);
    setQuoteDetail(null);
    setQuoteAttachments([]);
    setQuoteDetailError(null);
    setQuoteDetailLoading(true);
    setQuoteAttachmentsLoading(true);
    try {
      const [detail, attachments] = await Promise.all([
        getSafeQuoteDetail(id),
        listQuoteAttachments(id),
      ]);
      setQuoteDetail(detail);
      setQuoteAttachments(attachments);
    } catch (e: unknown) {
      setQuoteDetailError(e instanceof Error ? e.message : "Failed to load quote details");
    } finally {
      setQuoteDetailLoading(false);
      setQuoteAttachmentsLoading(false);
    }
  }, []);

  const searchActive = debouncedSearch.length > 0;

  return (
    <div className="space-y-6" data-testid="admin-dashboard-page">
      <PageHeader
        title="Admin Dashboard"
        subtitle="Track synced eWorks quotes and operational status."
      />

      <DashboardSearch value={searchInput} onChange={setSearchInput} />

      {loading ? (
        <LoadingState message="Loading dashboard…" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void load()} />
      ) : dashboard ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div data-testid="kpi-new-quotes">
              <StatCard
                label="New Quotes"
                value={dashboard.categories.new_quotes.count}
                className="border-t-2 border-t-blue-500"
              />
            </div>
            <div data-testid="kpi-awaiting-supplier">
              <StatCard
                label="Awaiting Supplier"
                value={dashboard.categories.awaiting_supplier.count}
                className="border-t-2 border-t-amber-500"
              />
            </div>
            <div data-testid="kpi-ready-to-send">
              <StatCard
                label="Ready to Send"
                value={dashboard.categories.ready_to_send.count}
                className="border-t-2 border-t-emerald-500"
              />
            </div>
            <div data-testid="kpi-last-sync">
              <StatCard
                label="Last Sync"
                value={
                  dashboard.last_synced_at ? (
                    <DateText value={dashboard.last_synced_at} includeTime />
                  ) : (
                    "—"
                  )
                }
              />
            </div>
          </div>

          <QuoteBucketBoard
            searchActive={searchActive}
            newQuotes={{
              title: "New Quotes",
              count: dashboard.categories.new_quotes.count,
              filteredCount: dashboard.categories.new_quotes.filtered_count,
              quotes: dashboard.categories.new_quotes.quotes,
              viewAllHref: buildAdminQuotesFilterUrl({ tab: "quotes", status: "1" }),
              testId: "category-new-quotes",
              viewAllTestId: "view-all-new_quotes",
            }}
            awaitingSupplier={{
              title: "Quotes Awaiting Supplier",
              count: dashboard.categories.awaiting_supplier.count,
              filteredCount: dashboard.categories.awaiting_supplier.filtered_count,
              quotes: dashboard.categories.awaiting_supplier.quotes,
              viewAllHref: buildAdminQuotesFilterUrl({ tab: "quotes", status: "1", tag: AWAITING_SUPPLIER_TAG }),
              testId: "category-awaiting-supplier",
              viewAllTestId: "view-all-awaiting_supplier",
            }}
            readyToSend={{
              title: "Quotes Ready to Send",
              count: dashboard.categories.ready_to_send.count,
              filteredCount: dashboard.categories.ready_to_send.filtered_count,
              quotes: dashboard.categories.ready_to_send.quotes,
              viewAllHref: buildAdminQuotesFilterUrl({ tab: "quotes", status: "1", tag: READY_TO_SEND_TAG }),
              testId: "category-ready-to-send",
              viewAllTestId: "view-all-ready_to_send",
            }}
            onQuoteClick={(id) => void openQuoteDetail(id)}
          />

          <SectionCard title="Admin tools" testId="admin-tools-section">
            <div className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard label="Users" value={dashboard.admin_stats.users} />
              <StatCard label="Products" value={dashboard.admin_stats.products} />
              <StatCard label="Audit logs" value={dashboard.admin_stats.audit_logs} />
              <StatCard
                label="eWorks API"
                value={
                  <StatusBadge tone={dashboard.admin_stats.eworks_api_enabled ? "success" : "neutral"}>
                    {dashboard.admin_stats.eworks_api_enabled ? "Enabled" : "Disabled"}
                  </StatusBadge>
                }
              />
            </div>
            <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {adminToolLinks.map((link) => {
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
        </>
      ) : null}

      {selectedQuoteId !== null ? (
        <QuoteDetailModal
          detail={quoteDetail}
          quoteId={selectedQuoteId}
          attachments={quoteAttachments}
          attachmentsLoading={quoteAttachmentsLoading}
          loading={quoteDetailLoading}
          error={quoteDetailError}
          allowSalesAppointmentBackfill
          onClose={() => {
            setSelectedQuoteId(null);
            setQuoteDetail(null);
            setQuoteAttachments([]);
            setQuoteDetailError(null);
          }}
        />
      ) : null}
    </div>
  );
}
