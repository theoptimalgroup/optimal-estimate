"use client";

import { useCallback, useEffect, useState } from "react";

import { ClientQuoteAcceptForm } from "@/components/client-quote-accept-form";
import {
  DateText,
  ErrorState,
  LoadingState,
  MoneyText,
  PrimaryButton,
  SectionCard,
  StatusBadge,
  quoteStatusTone,
} from "@/components/ui";
import {
  getPublicQuote,
  getPublicQuotePdfUrl,
  type PublicClientQuote,
} from "@/lib/client-quotes";

export default function ClientQuotePage({ params }: { params: { publicToken: string } }) {
  const { publicToken } = params;
  const [quote, setQuote] = useState<PublicClientQuote | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadQuote = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setQuote(await getPublicQuote(publicToken));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load quote");
      setQuote(null);
    } finally {
      setLoading(false);
    }
  }, [publicToken]);

  useEffect(() => {
    void loadQuote();
  }, [loadQuote]);

  return (
    <div className="min-h-screen bg-slate-50" data-testid="client-quote-page">
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">The Optimal Group</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Client Quote</h1>
            <p className="mt-1 text-sm text-slate-600">Professional estimate for your review</p>
          </div>
          {quote ? (
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-right">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Quote ref</p>
              <p className="mt-0.5 text-xl font-semibold text-slate-900">{quote.quote_ref}</p>
            </div>
          ) : null}
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-6 px-6 py-8">
        {loading ? (
          <LoadingState message="Loading your quote…" />
        ) : error ? (
          <div data-testid="client-quote-error">
            <ErrorState title="Quote unavailable" message={error} />
          </div>
        ) : quote ? (
          <div className="space-y-6">
            <SectionCard title="Quote details">
              <div className="grid gap-5 sm:grid-cols-2">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Client</p>
                  <p className="mt-1 font-medium text-slate-900">{quote.client_name}</p>
                </div>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Trade</p>
                  <p className="mt-1 font-medium text-slate-900">{quote.trade_name}</p>
                </div>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Quote date</p>
                  <p className="mt-1">
                    <DateText value={quote.submitted_at ?? quote.created_at} />
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Status</p>
                  <p className="mt-1">
                    <StatusBadge tone={quoteStatusTone(quote.status)}>
                      {quote.status.replace("_", " ")}
                    </StatusBadge>
                  </p>
                </div>
              </div>
            </SectionCard>

            {quote.scope_of_work ? (
              <SectionCard title="Scope of Work">
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{quote.scope_of_work}</p>
              </SectionCard>
            ) : null}

            {quote.works.length > 0 ? (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold text-slate-900">Works</h2>
                {quote.works.map((work) => (
                  <SectionCard key={work.title} title={work.title}>
                    {work.product_name ? <p className="text-sm text-slate-600">{work.product_name}</p> : null}
                    {work.scope ? (
                      <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{work.scope}</p>
                    ) : null}
                    {work.description ? (
                      <p className="mt-3 whitespace-pre-wrap text-sm text-slate-600">{work.description}</p>
                    ) : null}
                    {work.materials_summary ? (
                      <p className="mt-3 text-sm text-slate-600">Materials: {work.materials_summary}</p>
                    ) : null}
                  </SectionCard>
                ))}
              </div>
            ) : null}

            <div data-testid="client-quote-summary">
              <SectionCard title="Quote Summary">
                <dl className="space-y-3 text-sm">
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-600">Work charges</dt>
                    <dd className="text-right"><MoneyText value={quote.summary.work_charges} /></dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-600">Materials</dt>
                    <dd className="text-right"><MoneyText value={quote.summary.materials} /></dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-600">Additional charges</dt>
                    <dd className="text-right"><MoneyText value={quote.summary.additional_charges} /></dd>
                  </div>
                  <div className="flex justify-between gap-4 border-t border-slate-200 pt-3">
                    <dt className="text-slate-600">Subtotal</dt>
                    <dd className="text-right"><MoneyText value={quote.summary.subtotal} /></dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-600">VAT</dt>
                    <dd className="text-right"><MoneyText value={quote.summary.vat} /></dd>
                  </div>
                </dl>
                <div className="mt-5 flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-slate-50 px-5 py-4">
                  <dt className="text-base font-semibold text-slate-900">Total (inc. VAT)</dt>
                  <dd>
                    <MoneyText value={quote.summary.total} className="text-2xl font-bold text-slate-900" />
                  </dd>
                </div>
              </SectionCard>
            </div>

            <div className="flex flex-wrap gap-3">
              <a href={getPublicQuotePdfUrl(publicToken)} target="_blank" rel="noopener noreferrer">
                <PrimaryButton type="button">Download PDF</PrimaryButton>
              </a>
            </div>

            <ClientQuoteAcceptForm
              publicToken={publicToken}
              acceptance={quote.acceptance}
              onAccepted={() => void loadQuote()}
            />

            {quote.terms ? (
              <footer className="rounded-xl border border-slate-200 bg-white px-6 py-5 text-sm leading-relaxed text-slate-600 shadow-sm">
                <p>{quote.terms}</p>
                <p className="mt-3 text-slate-500">Contact The Optimal Group to discuss this quote.</p>
              </footer>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-slate-500">Quote not available.</p>
        )}
      </main>
    </div>
  );
}
