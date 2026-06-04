"use client";

import { useCallback, useEffect, useState } from "react";

import { EworksButton, EworksLoadingScreen } from "@/components/eworks-ui";
import { ClientQuoteAcceptForm } from "@/components/client-quote-accept-form";
import {
  formatMoney,
  formatQuoteDate,
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
    <div className="min-h-screen bg-gray-50" data-testid="client-quote-page">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-700">The Optimal Group</p>
            <h1 className="mt-1 text-2xl font-semibold text-gray-900">Client Quote</h1>
          </div>
          {quote ? (
            <div className="text-right">
              <p className="text-sm text-gray-500">Quote ref</p>
              <p className="text-lg font-semibold text-gray-900">{quote.quote_ref}</p>
            </div>
          ) : null}
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        {loading ? (
          <EworksLoadingScreen message="Loading your quote…" />
        ) : error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" data-testid="client-quote-error">
            {error}
          </div>
        ) : quote ? (
          <div className="space-y-6">
            <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm text-gray-500">Client</p>
                  <p className="font-medium text-gray-900">{quote.client_name}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Trade</p>
                  <p className="font-medium text-gray-900">{quote.trade_name}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Quote date</p>
                  <p className="font-medium text-gray-900">{formatQuoteDate(quote.submitted_at ?? quote.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Status</p>
                  <p className="font-medium capitalize text-gray-900">{quote.status.replace("_", " ")}</p>
                </div>
              </div>
            </section>

            {quote.scope_of_work ? (
              <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-gray-900">Scope of Work</h2>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-gray-700">{quote.scope_of_work}</p>
              </section>
            ) : null}

            {quote.works.length > 0 ? (
              <section className="space-y-4">
                <h2 className="text-lg font-semibold text-gray-900">Works</h2>
                {quote.works.map((work) => (
                  <article key={work.title} className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
                    <h3 className="font-semibold text-gray-900">{work.title}</h3>
                    {work.product_name ? <p className="mt-1 text-sm text-gray-600">{work.product_name}</p> : null}
                    {work.scope ? (
                      <p className="mt-3 whitespace-pre-wrap text-sm text-gray-700">{work.scope}</p>
                    ) : null}
                    {work.description ? (
                      <p className="mt-3 whitespace-pre-wrap text-sm text-gray-600">{work.description}</p>
                    ) : null}
                    {work.materials_summary ? (
                      <p className="mt-3 text-sm text-gray-600">Materials: {work.materials_summary}</p>
                    ) : null}
                  </article>
                ))}
              </section>
            ) : null}

            <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm" data-testid="client-quote-summary">
              <h2 className="text-lg font-semibold text-gray-900">Quote Summary</h2>
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-600">Work charges</dt>
                  <dd className="font-medium text-gray-900">{formatMoney(quote.summary.work_charges)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600">Materials</dt>
                  <dd className="font-medium text-gray-900">{formatMoney(quote.summary.materials)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600">Additional charges</dt>
                  <dd className="font-medium text-gray-900">{formatMoney(quote.summary.additional_charges)}</dd>
                </div>
                <div className="flex justify-between border-t border-gray-100 pt-3">
                  <dt className="text-gray-600">Subtotal</dt>
                  <dd className="font-medium text-gray-900">{formatMoney(quote.summary.subtotal)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600">VAT</dt>
                  <dd className="font-medium text-gray-900">{formatMoney(quote.summary.vat)}</dd>
                </div>
                <div className="flex justify-between border-t border-gray-200 pt-3 text-base">
                  <dt className="font-semibold text-gray-900">Total</dt>
                  <dd className="font-bold text-indigo-700">{formatMoney(quote.summary.total)}</dd>
                </div>
              </dl>
            </section>

            <section className="flex flex-wrap gap-3">
              <a href={getPublicQuotePdfUrl(publicToken)} target="_blank" rel="noopener noreferrer">
                <EworksButton type="button">Download PDF</EworksButton>
              </a>
            </section>

            <ClientQuoteAcceptForm
              publicToken={publicToken}
              acceptance={quote.acceptance}
              onAccepted={() => void loadQuote()}
            />

            {quote.terms ? (
              <footer className="rounded-lg border border-gray-200 bg-white p-5 text-sm text-gray-600 shadow-sm">
                <p>{quote.terms}</p>
                <p className="mt-3">Contact The Optimal Group to discuss this quote.</p>
              </footer>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-gray-500">Quote not available.</p>
        )}
      </main>
    </div>
  );
}
