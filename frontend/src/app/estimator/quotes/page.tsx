"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EstimatorQuotesTable } from "@/components/estimator/estimator-quotes-table";
import { EworksButton, EworksInput, EworksLabel, EworksLoadingScreen } from "@/components/eworks-ui";
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
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Quotes</h1>
        <p className="mt-2 text-sm text-gray-600">Browse and continue in-progress or submitted estimates</p>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div>
            <EworksLabel htmlFor="quotes-search">Search</EworksLabel>
            <EworksInput
              id="quotes-search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Quote ref, client, trade…"
            />
          </div>
          <div>
            <EworksLabel htmlFor="quotes-status">Status</EworksLabel>
            <select
              id="quotes-status"
              value={status}
              onChange={(e) => {
                setOffset(0);
                setStatus(e.target.value);
              }}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm"
            >
              <option value="all">All</option>
              <option value="in_progress">In progress</option>
              <option value="submitted">Submitted</option>
              <option value="reopened">Needs changes</option>
            </select>
          </div>
          <div>
            <EworksLabel htmlFor="quotes-date-from">Date from</EworksLabel>
            <EworksInput id="quotes-date-from" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div>
            <EworksLabel htmlFor="quotes-date-to">Date to</EworksLabel>
            <EworksInput id="quotes-date-to" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <EworksButton
            type="button"
            onClick={() => {
              setOffset(0);
              setSearch(searchInput.trim());
            }}
          >
            Apply
          </EworksButton>
          <EworksButton type="button" onClick={() => void loadQuotes()} disabled={loading}>
            Refresh
          </EworksButton>
        </div>
      </div>

      {loading ? (
        <EworksLoadingScreen message="Loading quotes…" />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : (
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <EstimatorQuotesTable quotes={quotes} showWorks showSubmitted />
          <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
            <span>
              Showing {quotes.length} of {total}
            </span>
            <div className="flex gap-2">
              <EworksButton type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                Previous
              </EworksButton>
              <EworksButton type="button" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)}>
                Next
              </EworksButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
