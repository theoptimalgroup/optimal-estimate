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
  AWAITING_DESKTOP_INFO_TAG,
  AWAITING_INTERNAL_INFO_TAG,
  AWAITING_SUPPLIER_TAG,
  BOOKED_TAG,
  MUST_ATTEND_TAG,
  READY_TO_SEND_TAG,
  buildQuotesFilterUrl,
  getManagerDashboard,
  type ManagerDashboard,
} from "@/lib/manager-dashboard";
import {
  getSafeQuoteDetail,
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
    setQuoteDetailError(null);
    setQuoteDetailLoading(true);
    try {
      const detail = await getSafeQuoteDetail(id);
      setQuoteDetail(detail);
    } catch (e: unknown) {
      setQuoteDetailError(e instanceof Error ? e.message : "Failed to load quote details");
    } finally {
      setQuoteDetailLoading(false);
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
            <div data-testid="kpi-must-attend">
              <StatCard
                label="Must Attend"
                value={dashboard.categories.must_attend.count}
                className="border-t-2 border-t-rose-500"
              />
            </div>
            <div data-testid="kpi-booked">
              <StatCard
                label="Booked"
                value={dashboard.categories.booked.count}
                className="border-t-2 border-t-violet-500"
              />
            </div>
            <div data-testid="kpi-awaiting-desktop-info">
              <StatCard
                label="Awaiting Desktop Info"
                value={dashboard.categories.awaiting_desktop_info.count}
                className="border-t-2 border-t-teal-500"
              />
            </div>
            <div data-testid="kpi-awaiting-internal-info">
              <StatCard
                label="Awaiting Internal Info"
                value={dashboard.categories.awaiting_internal_info.count}
                className="border-t-2 border-t-orange-500"
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
            <div data-testid="kpi-total-drafts">
              <StatCard
                label="Total Drafts"
                value={dashboard.totals.total_draft_quotes ?? dashboard.totals.all_open_quotes}
                className="border-t-2 border-t-slate-500"
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
              viewAllHref: buildQuotesFilterUrl({ type: "quotes", status: "1", tag: AWAITING_SUPPLIER_TAG }),
              testId: "category-awaiting-supplier",
              viewAllTestId: "view-all-awaiting_supplier",
            }}
            readyToSend={{
              title: "Quotes Ready to Send",
              count: dashboard.categories.ready_to_send.count,
              filteredCount: dashboard.categories.ready_to_send.filtered_count,
              quotes: dashboard.categories.ready_to_send.quotes,
              viewAllHref: buildQuotesFilterUrl({ type: "quotes", status: "1", tag: READY_TO_SEND_TAG }),
              testId: "category-ready-to-send",
              viewAllTestId: "view-all-ready_to_send",
            }}
            booked={{
              title: "Booked",
              count: dashboard.categories.booked.count,
              filteredCount: dashboard.categories.booked.filtered_count,
              quotes: dashboard.categories.booked.quotes,
              viewAllHref: buildQuotesFilterUrl({ type: "quotes", status: "1", tag: BOOKED_TAG }),
              testId: "category-booked",
              viewAllTestId: "view-all-booked",
            }}
            mustAttend={{
              title: "Must Attend",
              count: dashboard.categories.must_attend.count,
              filteredCount: dashboard.categories.must_attend.filtered_count,
              quotes: dashboard.categories.must_attend.quotes,
              viewAllHref: buildQuotesFilterUrl({ type: "quotes", status: "1", tag: MUST_ATTEND_TAG }),
              testId: "category-must-attend",
              viewAllTestId: "view-all-must_attend",
            }}
            awaitingDesktopInfo={{
              title: "Awaiting Desktop Info",
              count: dashboard.categories.awaiting_desktop_info.count,
              filteredCount: dashboard.categories.awaiting_desktop_info.filtered_count,
              quotes: dashboard.categories.awaiting_desktop_info.quotes,
              viewAllHref: buildQuotesFilterUrl({ type: "quotes", status: "1", tag: AWAITING_DESKTOP_INFO_TAG }),
              testId: "category-awaiting-desktop-info",
              viewAllTestId: "view-all-awaiting_desktop_info",
            }}
            awaitingInternalInfo={{
              title: "Awaiting Internal Info",
              count: dashboard.categories.awaiting_internal_info.count,
              filteredCount: dashboard.categories.awaiting_internal_info.filtered_count,
              quotes: dashboard.categories.awaiting_internal_info.quotes,
              viewAllHref: buildQuotesFilterUrl({ type: "quotes", status: "1", tag: AWAITING_INTERNAL_INFO_TAG }),
              testId: "category-awaiting-internal-info",
              viewAllTestId: "view-all-awaiting_internal_info",
            }}
            onQuoteClick={(id) => void openQuoteDetail(id)}
          />
        </>
      ) : null}

      {selectedQuoteId !== null ? (
        <QuoteDetailModal
          detail={quoteDetail}
          quoteId={selectedQuoteId}
          loading={quoteDetailLoading}
          error={quoteDetailError}
          onClose={() => {
            setSelectedQuoteId(null);
            setQuoteDetail(null);
            setQuoteDetailError(null);
          }}
        />
      ) : null}
    </div>
  );
}
