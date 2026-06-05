"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EstimatorQuotesTable } from "@/components/estimator/estimator-quotes-table";
import { AssignmentEstimateButton } from "@/components/quote-assignment-estimate-button";
import {
  EmptyState,
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
import { listMyQuoteAssignments, type QuoteAssignment } from "@/lib/quote-assignments";

const PAGE_SIZE = 25;

export default function EstimatorQuotesPage() {
  const [quotes, setQuotes] = useState<EstimatorQuoteRow[]>([]);
  const [assignedQuotes, setAssignedQuotes] = useState<QuoteAssignment[]>([]);
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
      const [result, assignments] = await Promise.all([
        listEstimatorQuotes(filters),
        listMyQuoteAssignments(),
      ]);
      setQuotes(result.items);
      setTotal(result.total);
      setAssignedQuotes(assignments.filter((item) => item.assignment_type === "estimator"));
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

      <SectionCard title="Assigned Quotes" testId="estimator-quotes-assigned">
        {assignedQuotes.length === 0 ? (
          <EmptyState
            title="No assigned quotes"
            description="Quotes assigned to you by a manager will appear here."
            className="border-0 bg-transparent py-4"
          />
        ) : (
          <ul className="divide-y divide-slate-100">
            {assignedQuotes.map((item) => (
              <li
                key={item.id}
                className="flex items-center justify-between gap-4 py-3 text-sm first:pt-0 last:pb-0"
                data-testid={`estimator-quotes-assignment-${item.id}`}
              >
                <div>
                  <span className="font-medium text-slate-900">{item.quote_ref ?? item.eworks_quote_id}</span>
                  <span className="ml-2 text-slate-600">
                    {item.quote_summary?.customer_name ?? "Customer not available"}
                  </span>
                </div>
                <AssignmentEstimateButton
                  assignment={item}
                  variant="link"
                  testId={`estimator-quotes-start-${item.id}`}
                />
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

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
