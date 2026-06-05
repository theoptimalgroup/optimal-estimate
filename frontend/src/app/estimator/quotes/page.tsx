"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EstimatorQuotesTable } from "@/components/estimator/estimator-quotes-table";
import {
  ErrorState,
  FilterBar,
  FilterField,
  filterInputClass,
  filterSelectClass,
  LoadingState,
  PageHeader,
  PaginationBar,
  PrimaryButton,
  SecondaryButton,
  SectionCard,
} from "@/components/ui";

import { listEstimatorQuotes, type EstimatorQuoteRow } from "@/lib/estimator";

const PAGE_SIZE = 25;

export default function EstimatorQuotesPage() {
  const [quotes, setQuotes] = useState<EstimatorQuoteRow[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const filters = useMemo(
    () => ({
      search: search || undefined,
      status: status === "all" ? undefined : status,
      date_from: dateFrom ? `${dateFrom}T00:00:00Z` : undefined,
      date_to: dateTo ? `${dateTo}T23:59:59Z` : undefined,
      limit: PAGE_SIZE,
      offset,
    }),
    [search, status, dateFrom, dateTo, offset],
  );

  const loadQuotes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listEstimatorQuotes(filters);
      setQuotes(result.items);
      setTotal(result.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load quotes");
      setQuotes([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void loadQuotes();
  }, [loadQuotes]);

  return (
    <div className="space-y-6" data-testid="estimator-quotes-page">
      <PageHeader
        title="Quotes"
        description="Browse and continue in-progress or submitted estimates"
      />

      <FilterBar>
        <FilterField label="Search">
          <input
            id="quotes-search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Quote ref, client, trade…"
            className={filterInputClass}
          />
        </FilterField>
        <FilterField label="Status">
          <select
            id="quotes-status"
            value={status}
            onChange={(e) => {
              setOffset(0);
              setStatus(e.target.value);
            }}
            className={filterSelectClass}
          >
            <option value="all">All</option>
            <option value="in_progress">In progress</option>
            <option value="submitted">Submitted</option>
            <option value="reopened">Needs changes</option>
          </select>
        </FilterField>
        <FilterField label="Date from">
          <input
            id="quotes-date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className={filterInputClass}
          />
        </FilterField>
        <FilterField label="Date to">
          <input
            id="quotes-date-to"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className={filterInputClass}
          />
        </FilterField>
        <div className="flex w-full flex-wrap gap-2 sm:w-auto sm:pb-0.5">
          <PrimaryButton
            onClick={() => {
              setOffset(0);
              setSearch(searchInput.trim());
            }}
          >
            Apply
          </PrimaryButton>
          <SecondaryButton onClick={() => void loadQuotes()} disabled={loading}>
            Refresh
          </SecondaryButton>
        </div>
      </FilterBar>

      {loading ? (
        <LoadingState message="Loading quotes…" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void loadQuotes()} />
      ) : (
        <SectionCard padding="none">
          <EstimatorQuotesTable quotes={quotes} showWorks showSubmitted />
          <PaginationBar total={total} offset={offset} limit={PAGE_SIZE} onPageChange={setOffset} />
        </SectionCard>
      )}
    </div>
  );
}
