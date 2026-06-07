"use client";

import { useCallback, useEffect, useState } from "react";

import { DashboardSearch } from "@/components/dashboard/dashboard-search";
import { QuoteBucketBoard } from "@/components/manager/quote-bucket-board";
import { QuoteDetailModal } from "@/components/manager/sync-detail-modals";
import {
  DateText,
  ErrorState,
  LoadingState,
  PageHeader,
  StatCard,
} from "@/components/ui";
import {
  AWAITING_SUPPLIER_TAG,
  READY_TO_SEND_TAG,
  buildQuotesFilterUrl,
  getManagerDashboard,
  type ManagerDashboard,
} from "@/lib/manager-dashboard";
import {
  getSafeQuoteDetail,
  listQuoteAttachments,
  type EworksAttachmentSafe,
  type EworksQuoteSafeDetail,
} from "@/lib/eworks-sync";

export default function ManagerDashboardPage() {
  const [dashboard, setDashboard] = useState<ManagerDashboard | null>(null);
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
      const data = await getManagerDashboard(10, debouncedSearch || undefined);
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
    <div className="space-y-6" data-testid="manager-dashboard-page">
      <PageHeader
        title="Manager Dashboard"
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
              viewAllHref: buildQuotesFilterUrl({ type: "quotes", status: "1" }),
              testId: "category-new-quotes",
              viewAllTestId: "view-all-new_quotes",
            }}
            awaitingSupplier={{
              title: "Quotes Awaiting Supplier",
              count: dashboard.categories.awaiting_supplier.count,
              filteredCount: dashboard.categories.awaiting_supplier.filtered_count,
              quotes: dashboard.categories.awaiting_supplier.quotes,
              viewAllHref: buildQuotesFilterUrl({ type: "quotes", tag: AWAITING_SUPPLIER_TAG }),
              testId: "category-awaiting-supplier",
              viewAllTestId: "view-all-awaiting_supplier",
            }}
            readyToSend={{
              title: "Quotes Ready to Send",
              count: dashboard.categories.ready_to_send.count,
              filteredCount: dashboard.categories.ready_to_send.filtered_count,
              quotes: dashboard.categories.ready_to_send.quotes,
              viewAllHref: buildQuotesFilterUrl({ type: "quotes", tag: READY_TO_SEND_TAG }),
              testId: "category-ready-to-send",
              viewAllTestId: "view-all-ready_to_send",
            }}
            onQuoteClick={(id) => void openQuoteDetail(id)}
          />
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
