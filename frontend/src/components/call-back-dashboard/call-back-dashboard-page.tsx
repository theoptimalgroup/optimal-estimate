"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardSearch } from "@/components/dashboard/dashboard-search";
import {
  ErrorState,
  LoadingState,
  MoneyText,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionCard,
  StatCard,
  StatusBadge,
} from "@/components/ui";
import {
  BUCKET_LABELS,
  CALL_STATUS_LABELS,
  getCallBackDashboard,
  patchCallBackTracking,
  type CallBackBucket,
  type CallBackDashboard,
  type CallBackDashboardQuote,
} from "@/lib/call-back-dashboard";

const BUCKETS: CallBackBucket[] = ["overdue", "due_today", "upcoming", "no_call_date"];

type Props = {
  apiBase: "manager" | "admin";
};

function callStatusTone(status: CallBackDashboardQuote["call_status"]) {
  switch (status) {
    case "overdue":
      return "error" as const;
    case "due_today":
      return "warning" as const;
    case "upcoming":
      return "info" as const;
    case "completed":
      return "success" as const;
    default:
      return "neutral" as const;
  }
}

function CallBackQuoteCard({
  quote,
  onUpdated,
}: {
  quote: CallBackDashboardQuote;
  onUpdated: () => void;
}) {
  const [note, setNote] = useState(quote.call_note ?? "");
  const [assigneeName, setAssigneeName] = useState(quote.assigned_name ?? "");
  const [assigneeEmail, setAssigneeEmail] = useState(quote.assigned_email ?? "");
  const [nextCall, setNextCall] = useState(
    quote.next_call_at ? quote.next_call_at.slice(0, 10) : "",
  );
  const [saving, setSaving] = useState(false);

  const saveDetails = async () => {
    setSaving(true);
    try {
      await patchCallBackTracking(quote.id, {
        call_note: note,
        assigned_name: assigneeName.trim() || null,
        assigned_email: assigneeEmail.trim() || null,
        next_call_at: nextCall ? `${nextCall}T09:00:00Z` : null,
      });
      onUpdated();
    } finally {
      setSaving(false);
    }
  };

  const logCallCompleted = async () => {
    setSaving(true);
    try {
      await patchCallBackTracking(quote.id, {
        last_called_at: new Date().toISOString(),
        next_call_at: null,
      });
      onUpdated();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm"
      data-testid={`call-back-quote-${quote.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-slate-900">{quote.quote_ref ?? `Quote ${quote.eworks_quote_id}`}</p>
          <p className="text-xs text-slate-600">{quote.customer_name ?? "Unknown customer"}</p>
          {quote.site_address ? <p className="text-xs text-slate-500">{quote.site_address}</p> : null}
        </div>
        <MoneyText value={quote.quote_value ?? 0} className="text-sm font-semibold text-slate-900" />
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        <StatusBadge tone={callStatusTone(quote.call_status)}>
          {CALL_STATUS_LABELS[quote.call_status]}
        </StatusBadge>
        <span className="text-[11px] text-slate-500">{quote.days_since_updated}d since update</span>
        {quote.status_name ? (
          <span className="text-[11px] text-slate-500">eWorks: {quote.status_name}</span>
        ) : null}
      </div>
      {quote.next_call_at ? (
        <p className="mt-1 text-xs text-slate-500">Next call: {quote.next_call_at.slice(0, 10)}</p>
      ) : null}
      <textarea
        className="mt-2 w-full rounded border border-slate-200 p-2 text-xs"
        rows={2}
        placeholder="Call note"
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        <input
          type="text"
          className="rounded border border-slate-200 px-2 py-1 text-xs"
          placeholder="Assigned name"
          value={assigneeName}
          onChange={(e) => setAssigneeName(e.target.value)}
          data-testid={`assignee-name-${quote.id}`}
        />
        <input
          type="email"
          className="rounded border border-slate-200 px-2 py-1 text-xs"
          placeholder="Assigned email"
          value={assigneeEmail}
          onChange={(e) => setAssigneeEmail(e.target.value)}
        />
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <input
          type="date"
          className="rounded border border-slate-200 px-2 py-1 text-xs"
          value={nextCall}
          onChange={(e) => setNextCall(e.target.value)}
          data-testid={`next-call-${quote.id}`}
        />
        <SecondaryButton type="button" disabled={saving} onClick={() => void saveDetails()}>
          Save
        </SecondaryButton>
        <SecondaryButton type="button" disabled={saving} onClick={() => void logCallCompleted()}>
          Log call
        </SecondaryButton>
        <Link href={quote.quote_detail_link} className="text-xs text-blue-600 underline">
          Open quote
        </Link>
      </div>
    </div>
  );
}

export function CallBackDashboardPage({ apiBase }: Props) {
  const [dashboard, setDashboard] = useState<CallBackDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(searchInput.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCallBackDashboard(apiBase, debouncedSearch || undefined);
      setDashboard(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load Call Back dashboard");
    } finally {
      setLoading(false);
    }
  }, [apiBase, debouncedSearch]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !dashboard) return <LoadingState message="Loading Call Back dashboard…" />;
  if (error && !dashboard) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!dashboard) return null;

  const { totals, categories } = dashboard;

  return (
    <div className="space-y-6" data-testid="call-back-dashboard-page">
      <PageHeader
        title="Call Back Dashboard"
        subtitle="eWorks Call Back quotes — local call tracking only (no eWorks writes)."
      />
      <DashboardSearch value={searchInput} onChange={setSearchInput} placeholder="Search quote ref or customer…" />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard label="Call Back Quotes" value={String(totals.call_back_quotes)} data-testid="kpi-call-back-quotes" />
        <StatCard label="Total Value" value={<MoneyText value={totals.total_quote_value} />} data-testid="kpi-total-value" />
        <StatCard label="Overdue Calls" value={String(totals.overdue_calls)} data-testid="kpi-overdue" />
        <StatCard label="Due Today" value={String(totals.due_today_calls)} data-testid="kpi-due-today" />
        <StatCard label="Upcoming" value={String(totals.upcoming_calls)} data-testid="kpi-upcoming" />
        <StatCard label="Average Age" value={`${totals.average_age_days}d`} data-testid="kpi-average-age" />
      </div>

      <SectionCard title="Call buckets" testId="call-back-buckets-section">
        <div className="grid gap-4 lg:grid-cols-4">
          {BUCKETS.map((bucket) => (
            <div key={bucket} data-testid={`call-back-bucket-${bucket}`}>
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-800">{BUCKET_LABELS[bucket]}</h3>
                <span className="text-xs text-slate-500">
                  {categories[bucket].count} · <MoneyText value={categories[bucket].value} />
                </span>
              </div>
              <div className="space-y-2">
                {categories[bucket].quotes.map((q) => (
                  <CallBackQuoteCard key={q.id} quote={q} onUpdated={() => void load()} />
                ))}
                {categories[bucket].quotes.length === 0 ? (
                  <p className="text-xs text-slate-400">No quotes in this bucket.</p>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      <div className="flex justify-end">
        <PrimaryButton type="button" onClick={() => void load()}>
          Refresh
        </PrimaryButton>
      </div>
    </div>
  );
}
