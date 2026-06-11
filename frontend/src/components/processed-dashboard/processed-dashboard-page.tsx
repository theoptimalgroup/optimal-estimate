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
  AGING_LABELS,
  BUCKET_LABELS,
  FOLLOW_UP_LABELS,
  getProcessedDashboard,
  patchSalesPipeline,
  type ProcessedDashboard,
  type ProcessedDashboardQuote,
  type SalesBucket,
} from "@/lib/processed-dashboard";

const BUCKETS: SalesBucket[] = ["pending", "possible", "strong", "dormant"];

type Props = {
  apiBase: "manager" | "admin";
};

function followUpTone(status: ProcessedDashboardQuote["follow_up_status"]) {
  switch (status) {
    case "overdue":
      return "error" as const;
    case "due_today":
      return "warning" as const;
    case "due_this_week":
      return "info" as const;
    default:
      return "neutral" as const;
  }
}

function PipelineQuoteCard({
  quote,
  onUpdated,
}: {
  quote: ProcessedDashboardQuote;
  onUpdated: () => void;
}) {
  const [note, setNote] = useState(quote.sales_note ?? "");
  const [assigneeName, setAssigneeName] = useState(quote.assigned_sales_name ?? "");
  const [assigneeEmail, setAssigneeEmail] = useState(quote.assigned_sales_email ?? "");
  const [nextFollowUp, setNextFollowUp] = useState(
    quote.next_follow_up_at ? quote.next_follow_up_at.slice(0, 10) : "",
  );
  const [saving, setSaving] = useState(false);

  const moveBucket = async (bucket: SalesBucket) => {
    setSaving(true);
    try {
      await patchSalesPipeline(quote.id, { sales_bucket: bucket });
      onUpdated();
    } finally {
      setSaving(false);
    }
  };

  const logFollowUp = async () => {
    setSaving(true);
    try {
      const today = new Date().toISOString();
      await patchSalesPipeline(quote.id, { last_follow_up_at: today });
      onUpdated();
    } finally {
      setSaving(false);
    }
  };

  const saveDetails = async () => {
    setSaving(true);
    try {
      await patchSalesPipeline(quote.id, {
        sales_note: note,
        assigned_sales_name: assigneeName.trim() || null,
        assigned_sales_email: assigneeEmail.trim() || null,
        next_follow_up_at: nextFollowUp ? `${nextFollowUp}T09:00:00Z` : null,
      });
      onUpdated();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm"
      data-testid={`pipeline-quote-${quote.id}`}
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
        <StatusBadge tone={followUpTone(quote.follow_up_status)}>
          {FOLLOW_UP_LABELS[quote.follow_up_status]}
        </StatusBadge>
        <span className="text-[11px] text-slate-500">{quote.days_since_processed}d processed</span>
        <span className="text-[11px] text-slate-500">{quote.days_in_current_bucket}d in bucket</span>
        {quote.eworks_status_name || quote.eworks_status ? (
          <span className="text-[11px] text-slate-500">
            eWorks: {quote.eworks_status_name ?? quote.eworks_status}
          </span>
        ) : null}
      </div>
      {quote.tags.length > 0 ? (
        <div className="mt-1 flex flex-wrap gap-1">
          {quote.tags.map((tag) => (
            <span
              key={tag}
              className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600"
            >
              {tag}
            </span>
          ))}
        </div>
      ) : null}
      {quote.next_follow_up_at ? (
        <p className="text-xs text-slate-500">Next follow-up: {quote.next_follow_up_at.slice(0, 10)}</p>
      ) : null}
      <div className="mt-2 flex flex-wrap gap-1">
        {BUCKETS.filter((b) => b !== quote.sales_bucket).map((b) => (
          <button
            key={b}
            type="button"
            disabled={saving}
            className="rounded border border-slate-200 px-2 py-0.5 text-[10px] text-slate-600 hover:bg-slate-50"
            onClick={() => void moveBucket(b)}
          >
            → {BUCKET_LABELS[b]}
          </button>
        ))}
      </div>
      <textarea
        className="mt-2 w-full rounded border border-slate-200 p-2 text-xs"
        rows={2}
        placeholder="Sales note"
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        <input
          type="text"
          className="rounded border border-slate-200 px-2 py-1 text-xs"
          placeholder="Salesperson name"
          value={assigneeName}
          onChange={(e) => setAssigneeName(e.target.value)}
          data-testid={`assignee-name-${quote.id}`}
        />
        <input
          type="email"
          className="rounded border border-slate-200 px-2 py-1 text-xs"
          placeholder="Salesperson email"
          value={assigneeEmail}
          onChange={(e) => setAssigneeEmail(e.target.value)}
          data-testid={`assignee-email-${quote.id}`}
        />
      </div>
      <div className="mt-2 flex items-center gap-2">
        <input
          type="date"
          className="rounded border border-slate-200 px-2 py-1 text-xs"
          value={nextFollowUp}
          onChange={(e) => setNextFollowUp(e.target.value)}
        />
        <SecondaryButton type="button" disabled={saving} onClick={() => void saveDetails()}>
          Save
        </SecondaryButton>
        <SecondaryButton type="button" disabled={saving} onClick={() => void logFollowUp()}>
          Log follow-up
        </SecondaryButton>
        <Link href={quote.quote_detail_link} className="text-xs text-blue-600 underline">
          Open quote
        </Link>
      </div>
    </div>
  );
}

export function ProcessedDashboardPage({ apiBase }: Props) {
  const [dashboard, setDashboard] = useState<ProcessedDashboard | null>(null);
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
      const data = await getProcessedDashboard(apiBase, debouncedSearch || undefined);
      setDashboard(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load sales pipeline");
    } finally {
      setLoading(false);
    }
  }, [apiBase, debouncedSearch]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !dashboard) return <LoadingState message="Loading sales pipeline…" />;
  if (error && !dashboard) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!dashboard) return null;

  const { totals, categories, aging, follow_up_reminders, salesperson_performance, accepted_rejected_trend, monthly_pipeline_value } = dashboard;

  return (
    <div className="space-y-6" data-testid="processed-dashboard-page">
      <PageHeader
        title="Sales Pipeline"
        subtitle="Processed quotes (eWorks status 2) — local pipeline tracking only."
      />
      <DashboardSearch value={searchInput} onChange={setSearchInput} placeholder="Search quote ref or customer…" />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard label="Processed Quotes" value={String(totals.processed_quotes)} data-testid="kpi-processed-quotes" />
        <StatCard label="Pipeline Value" value={<MoneyText value={totals.pipeline_value} />} data-testid="kpi-pipeline-value" />
        <StatCard label="Strong Value" value={<MoneyText value={totals.strong_value} />} data-testid="kpi-strong-value" />
        <StatCard label="Conversion Rate" value={`${totals.conversion_rate}%`} data-testid="kpi-conversion-rate" />
        <StatCard label="Overdue Follow-ups" value={String(totals.overdue_followups)} data-testid="kpi-overdue" />
        <StatCard label="Average Age" value={`${totals.average_age_days}d`} data-testid="kpi-average-age" />
      </div>

      <SectionCard title="Pipeline buckets" testId="pipeline-buckets-section">
        <div className="grid gap-4 lg:grid-cols-4">
          {BUCKETS.map((bucket) => (
            <div key={bucket} data-testid={`pipeline-bucket-${bucket}`}>
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-800">{BUCKET_LABELS[bucket]}</h3>
                <span className="text-xs text-slate-500">
                  {categories[bucket].count} · <MoneyText value={categories[bucket].value} />
                </span>
              </div>
              <div className="space-y-2">
                {categories[bucket].quotes.map((q) => (
                  <PipelineQuoteCard key={q.id} quote={q} onUpdated={() => void load()} />
                ))}
                {categories[bucket].quotes.length === 0 ? (
                  <p className="text-xs text-slate-400">No quotes in this bucket.</p>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Follow-up reminders" testId="follow-up-reminders-section">
          {(["overdue", "due_today", "due_this_week", "no_followup_set"] as const).map((key) => (
            <div key={key} className="mb-4">
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                {key === "no_followup_set" ? "No follow-up set" : key.replace(/_/g, " ")}
                {" "}({follow_up_reminders[key].length})
              </h4>
              <ul className="space-y-1 text-sm text-slate-700">
                {follow_up_reminders[key].slice(0, 5).map((q) => (
                  <li key={q.id}>
                    {q.quote_ref} — {q.customer_name}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </SectionCard>

        <SectionCard title="Aging" testId="aging-section">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500">
                <th className="pb-2">Bucket</th>
                <th className="pb-2">Count</th>
                <th className="pb-2">Value</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(aging).map(([key, row]) => (
                <tr key={key} className="border-t border-slate-100">
                  <td className="py-2">{AGING_LABELS[key] ?? key}</td>
                  <td className="py-2">{row.count}</td>
                  <td className="py-2">
                    <MoneyText value={row.value} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </SectionCard>
      </div>

      <SectionCard title="Salesperson performance" testId="salesperson-performance-section">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="pb-2">Salesperson</th>
              <th className="pb-2">Assigned</th>
              <th className="pb-2">Pipeline</th>
              <th className="pb-2">Strong</th>
              <th className="pb-2">Conv %</th>
              <th className="pb-2">Overdue</th>
              <th className="pb-2">Avg days to close</th>
            </tr>
          </thead>
          <tbody>
            {salesperson_performance.map((row, i) => (
              <tr key={i} className="border-t border-slate-100">
                <td className="py-2">{row.salesperson_name ?? row.salesperson_email ?? "Unassigned"}</td>
                <td className="py-2">{row.assigned_count}</td>
                <td className="py-2">
                  <MoneyText value={row.pipeline_value} />
                </td>
                <td className="py-2">
                  <MoneyText value={row.strong_value} />
                </td>
                <td className="py-2">{row.conversion_rate}%</td>
                <td className="py-2">{row.overdue_followups}</td>
                <td className="py-2">
                  {row.average_days_to_close != null ? `${row.average_days_to_close}d` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </SectionCard>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Accepted vs rejected trend" testId="accepted-rejected-trend-section">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500">
                <th className="pb-2">Month</th>
                <th className="pb-2">Accepted</th>
                <th className="pb-2">Rejected</th>
              </tr>
            </thead>
            <tbody>
              {accepted_rejected_trend.map((row) => (
                <tr key={row.month} className="border-t border-slate-100">
                  <td className="py-2">{row.month}</td>
                  <td className="py-2">
                    {row.accepted_count} (<MoneyText value={row.accepted_value} />)
                  </td>
                  <td className="py-2">
                    {row.rejected_count} (<MoneyText value={row.rejected_value} />)
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </SectionCard>

        <SectionCard title="Monthly pipeline value" testId="monthly-pipeline-value-section">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500">
                <th className="pb-2">Month</th>
                <th className="pb-2">New processed</th>
                <th className="pb-2">Active</th>
                <th className="pb-2">Strong</th>
                <th className="pb-2">Accepted</th>
                <th className="pb-2">Rejected</th>
              </tr>
            </thead>
            <tbody>
              {monthly_pipeline_value.map((row) => (
                <tr key={row.month} className="border-t border-slate-100">
                  <td className="py-2">{row.month}</td>
                  <td className="py-2">
                    <MoneyText value={row.new_processed_value} />
                  </td>
                  <td className="py-2">
                    <MoneyText value={row.active_pipeline_value} />
                  </td>
                  <td className="py-2">
                    <MoneyText value={row.strong_pipeline_value} />
                  </td>
                  <td className="py-2">
                    <MoneyText value={row.accepted_value} />
                  </td>
                  <td className="py-2">
                    <MoneyText value={row.rejected_value} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </SectionCard>
      </div>

      <div className="flex justify-end">
        <PrimaryButton type="button" onClick={() => void load()}>
          Refresh
        </PrimaryButton>
      </div>
    </div>
  );
}
