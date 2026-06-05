"use client";

import Link from "next/link";
import type { KeyboardEvent } from "react";

import { DateText, StatusBadge } from "@/components/ui";
import type { ManagerDashboardQuoteRow } from "@/lib/manager-dashboard";

type BucketAccent = "blue" | "amber" | "emerald";

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
};

function fmtMoney(val: number | null | undefined): string | null {
  if (val === null || val === undefined) return null;
  return `£${val.toFixed(2)}`;
}

function CompactTagBadges({ tags }: { tags?: string[] }) {
  if (!tags?.length) {
    return null;
  }

  const visible = tags.slice(0, 2);
  const extra = tags.length - visible.length;

  return (
    <div className="flex flex-wrap gap-1">
      {visible.map((tag) => (
        <StatusBadge key={tag} tone="info">
          {tag}
        </StatusBadge>
      ))}
      {extra > 0 ? (
        <StatusBadge tone="neutral">+{extra}</StatusBadge>
      ) : null}
    </div>
  );
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
  quote: ManagerDashboardQuoteRow;
  onClick: (id: number) => void;
}) {
  const total = fmtMoney(quote.total);
  const activate = () => onClick(quote.id);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`View details for quote ${quote.quote_ref ?? quote.id}`}
      className="cursor-pointer rounded-lg border border-slate-200 bg-slate-50 p-4 transition hover:border-blue-300 hover:bg-white hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
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
            <StatusBadge tone="neutral">{quote.status_name ?? quote.status}</StatusBadge>
          ) : null}
          <CompactTagBadges tags={quote.tags} />
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

        <p className="text-sm font-medium text-blue-600">View Details</p>
      </div>
    </div>
  );
}

export function QuoteBucketColumn({
  title,
  accent,
  count,
  quotes,
  viewAllHref,
  testId,
  viewAllTestId,
  onQuoteClick,
}: {
  title: string;
  accent: BucketAccent;
  count: number;
  quotes: ManagerDashboardQuoteRow[];
  viewAllHref: string;
  testId: string;
  viewAllTestId: string;
  onQuoteClick: (id: number) => void;
}) {
  const styles = ACCENT_STYLES[accent];

  return (
    <section
      className={`flex min-h-[18rem] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm border-t-4 ${styles.border}`}
      data-testid={testId}
    >
      <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-4">
        <div className="min-w-0 space-y-2">
          <h2 className="text-base font-semibold text-slate-900">{title}</h2>
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${styles.badge}`}
            data-testid={`${testId}-count`}
          >
            {count}
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

      <div className="flex flex-1 flex-col gap-3 p-4" data-testid={`${testId}-cards`}>
        {quotes.length === 0 ? (
          <div
            className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-600"
            data-testid={`${testId}-empty`}
          >
            No quotes in this category.
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

export function QuoteBucketBoard({
  newQuotes,
  awaitingSupplier,
  readyToSend,
  onQuoteClick,
}: {
  newQuotes: {
    title: string;
    count: number;
    quotes: ManagerDashboardQuoteRow[];
    viewAllHref: string;
    testId: string;
    viewAllTestId: string;
  };
  awaitingSupplier: {
    title: string;
    count: number;
    quotes: ManagerDashboardQuoteRow[];
    viewAllHref: string;
    testId: string;
    viewAllTestId: string;
  };
  readyToSend: {
    title: string;
    count: number;
    quotes: ManagerDashboardQuoteRow[];
    viewAllHref: string;
    testId: string;
    viewAllTestId: string;
  };
  onQuoteClick: (id: number) => void;
}) {
  return (
    <div className="grid gap-6 xl:grid-cols-3" data-testid="quote-bucket-board">
      <QuoteBucketColumn
        title={newQuotes.title}
        accent="blue"
        count={newQuotes.count}
        quotes={newQuotes.quotes}
        viewAllHref={newQuotes.viewAllHref}
        testId={newQuotes.testId}
        viewAllTestId={newQuotes.viewAllTestId}
        onQuoteClick={onQuoteClick}
      />
      <QuoteBucketColumn
        title={awaitingSupplier.title}
        accent="amber"
        count={awaitingSupplier.count}
        quotes={awaitingSupplier.quotes}
        viewAllHref={awaitingSupplier.viewAllHref}
        testId={awaitingSupplier.testId}
        viewAllTestId={awaitingSupplier.viewAllTestId}
        onQuoteClick={onQuoteClick}
      />
      <QuoteBucketColumn
        title={readyToSend.title}
        accent="emerald"
        count={readyToSend.count}
        quotes={readyToSend.quotes}
        viewAllHref={readyToSend.viewAllHref}
        testId={readyToSend.testId}
        viewAllTestId={readyToSend.viewAllTestId}
        onQuoteClick={onQuoteClick}
      />
    </div>
  );
}
