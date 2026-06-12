"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableRow,
  EmptyState,
  ErrorState,
  FilterBar,
  FilterField,
  LoadingState,
  PageHeader,
  PaginationBar,
  PageTabs,
  SecondaryButton,
  StatusBadge,
  TagBadges,
  filterInputClass,
} from "@/components/ui";
import { JobDetailModal, QuoteDetailModal } from "@/components/manager/sync-detail-modals";
import {
  getSafeJobDetail,
  getSafeQuoteDetail,
  listJobAttachments,
  formatEworksSyncError,
  listSyncedJobs,
  listSyncedQuotes,
  type EworksAttachmentSafe,
  type EworksJobRecord,
  type EworksJobSafeDetail,
  type EworksQuoteRecord,
  type EworksQuoteSafeDetail,
} from "@/lib/eworks-sync";

type TabId = "quotes" | "jobs";

const PAGE_SIZE = 50;

function fmtDate(val: string | null | undefined): string {
  if (!val) return "—";
  try {
    return new Date(val).toLocaleString();
  } catch {
    return val;
  }
}

function fmtMoney(val: number | null | undefined): string {
  if (val === null || val === undefined) return "—";
  return `£${val.toFixed(2)}`;
}

function quoteListCustomer(q: EworksQuoteRecord): string {
  return q.display_customer_name ?? q.customer_name ?? "Unknown Customer";
}

function quoteListStatus(q: EworksQuoteRecord): string | null {
  return q.display_status ?? q.status_name ?? null;
}

function quoteListTags(q: EworksQuoteRecord): string[] {
  return q.display_tags ?? q.tags ?? [];
}

function quoteListTotal(q: EworksQuoteRecord): number | null | undefined {
  return q.display_total ?? q.total;
}

function quoteListDate(q: EworksQuoteRecord): string {
  return q.display_quote_date ?? q.quote_date ?? "—";
}

function SharedFilters({
  search,
  customerName,
  status,
  tag,
  dateFrom,
  dateTo,
  onSearchChange,
  onCustomerNameChange,
  onStatusChange,
  onTagChange,
  onDateFromChange,
  onDateToChange,
  onRefresh,
  loading,
  searchTestId,
}: {
  search: string;
  customerName: string;
  status: string;
  tag: string;
  dateFrom: string;
  dateTo: string;
  onSearchChange: (value: string) => void;
  onCustomerNameChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onTagChange: (value: string) => void;
  onDateFromChange: (value: string) => void;
  onDateToChange: (value: string) => void;
  onRefresh: () => void;
  loading: boolean;
  searchTestId: string;
}) {
  return (
    <FilterBar>
      <FilterField label="Search">
        <input
          className={filterInputClass}
          placeholder="Ref, ID, customer, description…"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          data-testid={searchTestId}
        />
      </FilterField>
      <FilterField label="Customer">
        <input
          className={filterInputClass}
          placeholder="Customer name"
          value={customerName}
          onChange={(e) => onCustomerNameChange(e.target.value)}
        />
      </FilterField>
      <FilterField label="Status">
        <input
          className={filterInputClass}
          placeholder="Status"
          value={status}
          onChange={(e) => onStatusChange(e.target.value)}
        />
      </FilterField>
      <FilterField label="Tag">
        <input
          className={filterInputClass}
          placeholder="Tag"
          value={tag}
          onChange={(e) => onTagChange(e.target.value)}
          data-testid="tag-filter"
        />
      </FilterField>
      <FilterField label="Date from">
        <input
          type="date"
          className={filterInputClass}
          value={dateFrom}
          onChange={(e) => onDateFromChange(e.target.value)}
        />
      </FilterField>
      <FilterField label="Date to">
        <input
          type="date"
          className={filterInputClass}
          value={dateTo}
          onChange={(e) => onDateToChange(e.target.value)}
        />
      </FilterField>
      <FilterField label=" ">
        <SecondaryButton onClick={onRefresh} disabled={loading} data-testid="quotes-refresh">
          Refresh
        </SecondaryButton>
      </FilterField>
    </FilterBar>
  );
}

export default function ManagerQuotesPage() {
  const searchParams = useSearchParams();

  const initialType = searchParams.get("type") === "jobs" ? "jobs" : "quotes";
  const initialStatus = searchParams.get("status") ?? "";
  const initialTag = searchParams.get("tag") ?? "";

  const [activeTab, setActiveTab] = useState<TabId>(initialType);

  const [search, setSearch] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [status, setStatus] = useState(initialStatus);
  const [tag, setTag] = useState(initialTag);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [offset, setOffset] = useState(0);

  const [quoteItems, setQuoteItems] = useState<EworksQuoteRecord[]>([]);
  const [quoteTotal, setQuoteTotal] = useState(0);
  const [jobItems, setJobItems] = useState<EworksJobRecord[]>([]);
  const [jobTotal, setJobTotal] = useState(0);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedQuoteId, setSelectedQuoteId] = useState<number | null>(null);
  const [quoteDetail, setQuoteDetail] = useState<EworksQuoteSafeDetail | null>(null);
  const [quoteDetailLoading, setQuoteDetailLoading] = useState(false);
  const [quoteDetailError, setQuoteDetailError] = useState<string | null>(null);

  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [jobDetail, setJobDetail] = useState<EworksJobSafeDetail | null>(null);
  const [jobDetailLoading, setJobDetailLoading] = useState(false);
  const [jobDetailError, setJobDetailError] = useState<string | null>(null);
  const [jobAttachments, setJobAttachments] = useState<EworksAttachmentSafe[]>([]);
  const [jobAttachmentsLoading, setJobAttachmentsLoading] = useState(false);

  const resetOffset = useCallback(() => setOffset(0), []);

  useEffect(() => {
    const typeParam = searchParams.get("type") === "jobs" ? "jobs" : "quotes";
    setActiveTab(typeParam);
    setStatus(searchParams.get("status") ?? "");
    setTag(searchParams.get("tag") ?? "");
    setOffset(0);
  }, [searchParams]);

  const loadQuotes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listSyncedQuotes({
        search: search || undefined,
        customer_name: customerName || undefined,
        status: status || undefined,
        tag: tag || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setQuoteItems(result.items);
      setQuoteTotal(result.total);
    } catch (e: unknown) {
      setError(formatEworksSyncError(e, "Failed to load quotes"));
      setQuoteItems([]);
      setQuoteTotal(0);
    } finally {
      setLoading(false);
    }
  }, [search, customerName, status, tag, dateFrom, dateTo, offset]);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listSyncedJobs({
        search: search || undefined,
        customer_name: customerName || undefined,
        status: status || undefined,
        tag: tag || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setJobItems(result.items);
      setJobTotal(result.total);
    } catch (e: unknown) {
      setError(formatEworksSyncError(e, "Failed to load jobs"));
      setJobItems([]);
      setJobTotal(0);
    } finally {
      setLoading(false);
    }
  }, [search, customerName, status, tag, dateFrom, dateTo, offset]);

  const refresh = useCallback(() => {
    if (activeTab === "quotes") {
      void loadQuotes();
    } else {
      void loadJobs();
    }
  }, [activeTab, loadQuotes, loadJobs]);

  useEffect(() => {
    if (activeTab === "quotes") {
      void loadQuotes();
    } else {
      void loadJobs();
    }
  }, [activeTab, loadQuotes, loadJobs]);

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

  const openJobDetail = useCallback(async (id: number) => {
    setSelectedJobId(id);
    setJobDetail(null);
    setJobAttachments([]);
    setJobDetailError(null);
    setJobDetailLoading(true);
    setJobAttachmentsLoading(true);
    try {
      const [detail, attachments] = await Promise.all([
        getSafeJobDetail(id),
        listJobAttachments(id),
      ]);
      setJobDetail(detail);
      setJobAttachments(attachments);
    } catch (e: unknown) {
      setJobDetailError(e instanceof Error ? e.message : "Failed to load job details");
    } finally {
      setJobDetailLoading(false);
      setJobAttachmentsLoading(false);
    }
  }, []);

  return (
    <div className="space-y-6" data-testid="manager-quotes-page">
      <PageHeader title="Quotes" />

      <PageTabs
        tabs={[
          { id: "quotes" as const, label: "Quotes" },
          { id: "jobs" as const, label: "Jobs" },
        ]}
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          resetOffset();
        }}
      />

      <SharedFilters
        search={search}
        customerName={customerName}
        status={status}
        tag={tag}
        dateFrom={dateFrom}
        dateTo={dateTo}
        onSearchChange={(value) => {
          setSearch(value);
          resetOffset();
        }}
        onCustomerNameChange={(value) => {
          setCustomerName(value);
          resetOffset();
        }}
        onStatusChange={(value) => {
          setStatus(value);
          resetOffset();
        }}
        onTagChange={(value) => {
          setTag(value);
          resetOffset();
        }}
        onDateFromChange={(value) => {
          setDateFrom(value);
          resetOffset();
        }}
        onDateToChange={(value) => {
          setDateTo(value);
          resetOffset();
        }}
        onRefresh={refresh}
        loading={loading}
        searchTestId={activeTab === "quotes" ? "quotes-search" : "jobs-search"}
      />

      {error ? (
        <ErrorState message={error} onRetry={refresh} />
      ) : loading ? (
        <LoadingState message={activeTab === "quotes" ? "Loading quotes…" : "Loading jobs…"} />
      ) : activeTab === "quotes" ? (
        quoteItems.length === 0 ? (
          <EmptyState title="No synced quotes found." />
        ) : (
          <>
            <DataTable testId="quotes-table">
              <DataTableHead sticky>
                <DataTableCell header>Quote Ref</DataTableCell>
                <DataTableCell header>eWorks Quote ID</DataTableCell>
                <DataTableCell header>Customer</DataTableCell>
                <DataTableCell header>Status</DataTableCell>
                <DataTableCell header>Tags</DataTableCell>
                <DataTableCell header>Quote Date</DataTableCell>
                <DataTableCell header align="right">
                  Total
                </DataTableCell>
                <DataTableCell header>Synced At</DataTableCell>
                <DataTableCell header>Action</DataTableCell>
              </DataTableHead>
              <DataTableBody>
                {quoteItems.map((q) => (
                  <DataTableRow key={q.id} data-testid={`quote-row-${q.id}`}>
                    <DataTableCell>{q.quote_ref ?? "—"}</DataTableCell>
                    <DataTableCell>
                      <span className="font-mono text-xs">{q.eworks_quote_id}</span>
                    </DataTableCell>
                    <DataTableCell>{quoteListCustomer(q)}</DataTableCell>
                    <DataTableCell>
                      {quoteListStatus(q) ? (
                        <StatusBadge tone="neutral">{quoteListStatus(q)}</StatusBadge>
                      ) : (
                        "—"
                      )}
                    </DataTableCell>
                    <DataTableCell>
                      <TagBadges tags={quoteListTags(q)} />
                    </DataTableCell>
                    <DataTableCell className="whitespace-nowrap">{quoteListDate(q)}</DataTableCell>
                    <DataTableCell align="right" className="whitespace-nowrap tabular-nums">
                      {fmtMoney(quoteListTotal(q))}
                    </DataTableCell>
                    <DataTableCell className="whitespace-nowrap text-slate-600">{fmtDate(q.synced_at)}</DataTableCell>
                    <DataTableCell>
                      <SecondaryButton size="sm" onClick={() => void openQuoteDetail(q.id)} data-testid={`quote-view-${q.id}`}>
                        View
                      </SecondaryButton>
                    </DataTableCell>
                  </DataTableRow>
                ))}
              </DataTableBody>
            </DataTable>
            <PaginationBar
              total={quoteTotal}
              limit={PAGE_SIZE}
              offset={offset}
              onPageChange={setOffset}
            />
          </>
        )
      ) : jobItems.length === 0 ? (
        <EmptyState title="No synced jobs found." />
      ) : (
        <>
          <DataTable testId="jobs-table">
            <DataTableHead>
              <DataTableCell header>Job Ref</DataTableCell>
              <DataTableCell header>eWorks Job ID</DataTableCell>
              <DataTableCell header>Related Quote</DataTableCell>
              <DataTableCell header>Customer</DataTableCell>
              <DataTableCell header>Status</DataTableCell>
              <DataTableCell header>Tags</DataTableCell>
              <DataTableCell header>Job Date</DataTableCell>
              <DataTableCell header align="right">
                Total
              </DataTableCell>
              <DataTableCell header>Synced At</DataTableCell>
              <DataTableCell header>Action</DataTableCell>
            </DataTableHead>
            <DataTableBody>
              {jobItems.map((j) => (
                <DataTableRow key={j.id}>
                  <DataTableCell>{j.job_ref ?? "—"}</DataTableCell>
                  <DataTableCell>
                    <span className="font-mono text-xs">{j.eworks_job_id}</span>
                  </DataTableCell>
                  <DataTableCell>
                    {j.eworks_quote_id != null ? (
                      <span className="font-mono text-xs">{j.eworks_quote_id}</span>
                    ) : (
                      "—"
                    )}
                  </DataTableCell>
                  <DataTableCell>{j.customer_name ?? "—"}</DataTableCell>
                  <DataTableCell>
                    {j.status_name ? <StatusBadge tone="neutral">{j.status_name}</StatusBadge> : "—"}
                  </DataTableCell>
                  <DataTableCell>
                    <TagBadges tags={j.tags} />
                  </DataTableCell>
                  <DataTableCell>{j.job_date ?? "—"}</DataTableCell>
                  <DataTableCell align="right">{fmtMoney(j.total)}</DataTableCell>
                  <DataTableCell>{fmtDate(j.synced_at)}</DataTableCell>
                  <DataTableCell>
                    <SecondaryButton size="sm" onClick={() => void openJobDetail(j.id)} data-testid={`job-view-${j.id}`}>
                      View
                    </SecondaryButton>
                  </DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>
          <PaginationBar total={jobTotal} limit={PAGE_SIZE} offset={offset} onPageChange={setOffset} />
        </>
      )}

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

      {selectedJobId !== null ? (
        <JobDetailModal
          detail={jobDetail}
          attachments={jobAttachments}
          attachmentsLoading={jobAttachmentsLoading}
          loading={jobDetailLoading}
          error={jobDetailError}
          onClose={() => {
            setSelectedJobId(null);
            setJobDetail(null);
            setJobAttachments([]);
            setJobDetailError(null);
          }}
        />
      ) : null}
    </div>
  );
}
