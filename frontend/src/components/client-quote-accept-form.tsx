"use client";

import { useState } from "react";

import { EworksButton, EworksInput, EworksLabel } from "@/components/eworks-ui";
import { acceptPublicQuote, formatQuoteDate } from "@/lib/client-quotes";
import type { PublicQuoteAcceptance } from "@/lib/quote-acceptance";

type ClientQuoteAcceptFormProps = {
  publicToken: string;
  acceptance: PublicQuoteAcceptance;
  onAccepted: () => void;
};

export function ClientQuoteAcceptForm({ publicToken, acceptance, onAccepted }: ClientQuoteAcceptFormProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [notes, setNotes] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [justAccepted, setJustAccepted] = useState(false);

  const isAccepted = acceptance.accepted || justAccepted;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!confirmed || !name.trim() || !email.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      await acceptPublicQuote(publicToken, {
        name: name.trim(),
        email: email.trim(),
        notes: notes.trim() || undefined,
      });
      setJustAccepted(true);
      onAccepted();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to accept quote");
    } finally {
      setSubmitting(false);
    }
  };

  if (isAccepted) {
    return (
      <section
        className="rounded-lg border border-emerald-200 bg-emerald-50 p-6 shadow-sm"
        data-testid="client-quote-accepted"
      >
        {justAccepted ? (
          <p className="text-base font-medium text-emerald-900">Quote accepted. Thank you.</p>
        ) : (
          <p className="text-base font-medium text-emerald-900">
            This quote was accepted on {formatQuoteDate(acceptance.accepted_at)}
            {acceptance.name ? ` by ${acceptance.name}` : ""}.
          </p>
        )}
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm" data-testid="client-quote-accept-form">
      <h2 className="text-lg font-semibold text-gray-900">Accept Quote</h2>
      <p className="mt-2 text-sm text-gray-600">
        Confirm your acceptance below. No login is required.
      </p>

      <form className="mt-5 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
        <div>
          <EworksLabel htmlFor="accept-name">Your name</EworksLabel>
          <EworksInput
            id="accept-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            autoComplete="name"
            data-testid="accept-name-input"
          />
        </div>
        <div>
          <EworksLabel htmlFor="accept-email">Email</EworksLabel>
          <EworksInput
            id="accept-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
            data-testid="accept-email-input"
          />
        </div>
        <div>
          <EworksLabel htmlFor="accept-notes">Notes (optional)</EworksLabel>
          <textarea
            id="accept-notes"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            rows={3}
            maxLength={2000}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            data-testid="accept-notes-input"
          />
        </div>
        <label className="flex items-start gap-3 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(event) => setConfirmed(event.target.checked)}
            className="mt-1 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            data-testid="accept-confirm-checkbox"
          />
          <span>I confirm I accept this quote and agree to proceed.</span>
        </label>
        {error ? (
          <p className="text-sm text-red-600" data-testid="accept-error">
            {error}
          </p>
        ) : null}
        <EworksButton
          type="submit"
          disabled={submitting || !confirmed || !name.trim() || !email.trim()}
          data-testid="accept-quote-button"
        >
          {submitting ? "Submitting…" : "Accept Quote"}
        </EworksButton>
      </form>
    </section>
  );
}
