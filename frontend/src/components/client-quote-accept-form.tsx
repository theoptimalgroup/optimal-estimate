"use client";

import { useState } from "react";

import { EworksInput, EworksLabel } from "@/components/eworks-ui";
import {
  DateText,
  ErrorState,
  PrimaryButton,
  SectionCard,
  StatusBadge,
} from "@/components/ui";
import { acceptPublicQuote } from "@/lib/client-quotes";
import type { PublicQuoteAcceptance } from "@/lib/quote-acceptance";

type ClientQuoteAcceptFormProps = {
  publicToken: string;
  acceptance: PublicQuoteAcceptance;
  onAccepted: () => void;
};

const notesClass =
  "mt-1 block w-full min-h-[120px] rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-base text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30";

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
      <div data-testid="client-quote-accepted">
        <SectionCard className="border-emerald-200 bg-emerald-50/80">
          <div className="flex flex-wrap items-center gap-3">
            <StatusBadge tone="success">Accepted</StatusBadge>
            {justAccepted ? (
              <p className="text-base font-medium text-emerald-900">Quote accepted. Thank you.</p>
            ) : (
              <p className="text-base font-medium text-emerald-900">
                This quote was accepted on <DateText value={acceptance.accepted_at} includeTime />
                {acceptance.name ? ` by ${acceptance.name}` : ""}.
              </p>
            )}
          </div>
        </SectionCard>
      </div>
    );
  }

  return (
    <div data-testid="client-quote-accept-form">
      <SectionCard title="Accept Quote" description="Confirm your acceptance below. No login is required.">
        <form className="space-y-4" onSubmit={(event) => void handleSubmit(event)}>
          <div>
            <EworksLabel>Your name</EworksLabel>
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
            <EworksLabel>Email</EworksLabel>
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
            <EworksLabel>Notes (optional)</EworksLabel>
            <textarea
              id="accept-notes"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
              maxLength={2000}
              className={notesClass}
              data-testid="accept-notes-input"
            />
          </div>
          <label className="flex min-h-[44px] items-start gap-3 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
              className="mt-1 size-5 shrink-0 rounded border-slate-300 text-blue-600 focus:ring-blue-500/40"
              data-testid="accept-confirm-checkbox"
            />
            <span>I confirm I accept this quote and agree to proceed.</span>
          </label>
          {error ? (
            <div data-testid="accept-error">
              <ErrorState title="Acceptance failed" message={error} className="py-3" />
            </div>
          ) : null}
          <PrimaryButton
            type="submit"
            disabled={submitting || !confirmed || !name.trim() || !email.trim()}
            data-testid="accept-quote-button"
          >
            {submitting ? "Submitting…" : "Accept Quote"}
          </PrimaryButton>
        </form>
      </SectionCard>
    </div>
  );
}
