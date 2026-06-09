"use client";

import Link from "next/link";
import type { KeyboardEvent } from "react";

import { DateText, TagBadges } from "@/components/ui";
import type { DashboardQuoteRow } from "@/lib/dashboard-quotes";

type BucketAccent = "blue" | "amber" | "emerald" | "rose" | "violet" | "teal" | "orange";

const ACCENT_STYLES: Record<
  BucketAccent,
  { border: string; badge: string }
> = {
  blue: {
    border: "border-t-blue-500",
    badge: "bg-blue-50 text-blue-700 ring-blue-200",
  },
  amber: {
    border: "border-t-amber-500",
    badge: "bg-amber-50 text-amber-700 ring-amber-200",
  },
  emerald: {
    border: "border-t-emerald-500",
    badge: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  },
  rose: {
    border: "border-t-rose-500",
    badge: "bg-rose-50 text-rose-700 ring-rose-200",
  },
  violet: {
    border: "border-t-violet-500",
    badge: "bg-violet-50 text-violet-700 ring-violet-200",
  },
  teal: {
    border: "border-t-teal-500",
    badge: "bg-teal-50 text-teal-700 ring-teal-200",
  },
  orange: {
    border: "border-t-orange-500",
    badge: "bg-orange-50 text-orange-700 ring-orange-200",
  },
};

function fmtMoney(val: number | null | undefined): string | null {
  if (val === null || val === undefined) return null;
  return `£${val.toFixed(2)}`;
}

function handleCardKeyDown(
  event: KeyboardEvent<HTMLDivElement>,
  onActivate: () => void,
) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    onActivate();
  }
}

export function DashboardQuoteCard({
  quote,
  onClick,
}: {
  quote: DashboardQuoteRow;
  onClick: (id: number) => void;
}) {
  const total = fmtMoney(quote.total);
  const activate = () => onClick(quote.id);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`View details for quote ${quote.quote_ref ?? quote.id}`}
      className="cursor-pointer rounded-lg border border-slate-200 bg-white p-4 transition hover:border-blue-200 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
      data-testid={`dashboard-quote-card-${quote.id}`}
      onClick={activate}
      onKeyDown={(event) => handleCardKeyDown(event, activate)}
    >
      <div className="space-y-3">
        <div className="space-y-1">
          <p className="text-base font-semibold text-slate-900">{quote.quote_ref ?? "—"}</p>
          <p className="text-sm text-slate-600">
            {quote.customer_name?.trim() || "Customer not available"}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {quote.status_name || quote.status ? (
            <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
              {quote.status_name ?? quote.status}
            </span>
          ) : null}
          <TagBadges tags={quote.tags} compact maxVisible={2} emptyLabel="" />
        </div>

        <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Quote Date</dt>
            <dd className="mt-0.5 text-slate-900">{quote.quote_date ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Expiry Date</dt>
            <dd className="mt-0.5 text-slate-900">{quote.expiry_date ?? "—"}</dd>
          </div>
          {total ? (
            <div className="col-span-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Total</dt>
              <dd className="mt-0.5 font-medium text-slate-900">{total}</dd>
            </div>
          ) : null}
        </dl>

        {quote.synced_at ? (
          <p className="text-xs text-slate-500">
            Synced <DateText value={quote.synced_at} includeTime />
          </p>
        ) : null}
      </div>
    </div>
  );
}

function formatBucketCountLabel(
  count: number,
  filteredCount: number | null | undefined,
  searchActive: boolean,
): string {
  if (searchActive && filteredCount != null) {
    return `Showing ${filteredCount} of ${count}`;
  }
  return String(count);
}

export function QuoteBucketColumn({
  title,
  accent,
  count,
  filteredCount,
  searchActive = false,
  quotes,
  viewAllHref,
  testId,
  viewAllTestId,
  onQuoteClick,
}: {
  title: string;
  accent: BucketAccent;
  count: number;
  filteredCount?: number | null;
  searchActive?: boolean;
  quotes: DashboardQuoteRow[];
  viewAllHref: string;
  testId: string;
  viewAllTestId: string;
  onQuoteClick: (id: number) => void;
}) {
  const styles = ACCENT_STYLES[accent];
  const countLabel = formatBucketCountLabel(count, filteredCount, searchActive);
  const emptyMessage = searchActive
    ? "No matching quotes in this category."
    : "No quotes in this category.";

  return (
    <section
      className={`flex min-h-[18rem] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm border-t-4 ${styles.border}`}
      data-testid={testId}
    >
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <h2 className="text-base font-semibold text-slate-900">{title}</h2>
          <span
            className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-semibold tabular-nums ring-1 ring-inset ${styles.badge}`}
            data-testid={`${testId}-count`}
          >
            {countLabel}
          </span>
        </div>
        <Link
          href={viewAllHref}
          className="shrink-0 text-sm font-medium text-blue-600 hover:text-blue-700"
          data-testid={viewAllTestId}
          onClick={(event) => event.stopPropagation()}
        >
          View all
        </Link>
      </div>

      <div className="flex flex-1 flex-col gap-4 p-4" data-testid={`${testId}-cards`}>
        {quotes.length === 0 ? (
          <div
            className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-600"
            data-testid={`${testId}-empty`}
          >
            {emptyMessage}
          </div>
        ) : (
          quotes.map((quote) => (
            <DashboardQuoteCard key={quote.id} quote={quote} onClick={onQuoteClick} />
          ))
        )}
      </div>
    </section>
  );
}

type BucketColumnData = {
  title: string;
  count: number;
  filteredCount?: number | null;
  quotes: DashboardQuoteRow[];
  viewAllHref: string;
  testId: string;
  viewAllTestId: string;
};

export function QuoteBucketBoard({
  newQuotes,
  awaitingSupplier,
  readyToSend,
  booked,
  mustAttend,
  awaitingDesktopInfo,
  awaitingInternalInfo,
  searchActive = false,
  onQuoteClick,
}: {
  newQuotes: BucketColumnData;
  awaitingSupplier: BucketColumnData;
  readyToSend: BucketColumnData;
  booked: BucketColumnData;
  mustAttend: BucketColumnData;
  awaitingDesktopInfo: BucketColumnData;
  awaitingInternalInfo: BucketColumnData;
  searchActive?: boolean;
  onQuoteClick: (id: number) => void;
}) {
  const columns: Array<BucketColumnData & { accent: BucketAccent }> = [
    { ...newQuotes, accent: "blue" },
    { ...awaitingSupplier, accent: "amber" },
    { ...readyToSend, accent: "emerald" },
    { ...booked, accent: "violet" },
    { ...mustAttend, accent: "rose" },
    { ...awaitingDesktopInfo, accent: "teal" },
    { ...awaitingInternalInfo, accent: "orange" },
  ];

  return (
    <div
      className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
      data-testid="quote-bucket-board"
    >
      {columns.map((col) => (
        <QuoteBucketColumn
          key={col.testId}
          title={col.title}
          accent={col.accent}
          count={col.count}
          filteredCount={col.filteredCount}
          searchActive={searchActive}
          quotes={col.quotes}
          viewAllHref={col.viewAllHref}
          testId={col.testId}
          viewAllTestId={col.viewAllTestId}
          onQuoteClick={onQuoteClick}
        />
      ))}
    </div>
  );
}
