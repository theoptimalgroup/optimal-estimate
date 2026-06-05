"use client";

import { useState } from "react";

import { PrimaryButton, SecondaryButton, SectionCard } from "@/components/ui";
import {
  buildAbsoluteClientQuoteUrl,
  buildClientQuotePageUrl,
  createPublicQuoteLink,
  revokePublicQuoteLink,
} from "@/lib/client-quotes";

type ClientLinkPanelProps = {
  sessionId: string;
};

export function ClientLinkPanel({ sessionId }: ClientLinkPanelProps) {
  const [linkUrl, setLinkUrl] = useState<string | null>(null);
  const [publicToken, setPublicToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCreateLink = async () => {
    setLoading(true);
    setError(null);
    setCopied(false);
    try {
      const link = await createPublicQuoteLink(sessionId);
      setPublicToken(link.public_token);
      setLinkUrl(buildAbsoluteClientQuoteUrl(link.public_token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create client link");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!linkUrl) return;
    try {
      await navigator.clipboard.writeText(linkUrl);
      setCopied(true);
    } catch {
      setError("Unable to copy link to clipboard");
    }
  };

  const handleRevoke = async () => {
    setRevoking(true);
    setError(null);
    try {
      await revokePublicQuoteLink(sessionId);
      setLinkUrl(null);
      setPublicToken(null);
      setCopied(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to revoke client link");
    } finally {
      setRevoking(false);
    }
  };

  return (
    <div data-testid="client-link-panel">
      <SectionCard
        title="Client quote link"
        description="Generate a secure public link for the client to view this quote without staff login."
        className="border-blue-200 bg-blue-50/40"
        actions={
          <div className="flex flex-wrap gap-2">
            <PrimaryButton disabled={loading} onClick={() => void handleCreateLink()}>
              {loading ? "Creating…" : linkUrl ? "Refresh link" : "Create client link"}
            </PrimaryButton>
            {linkUrl ? (
              <>
                <SecondaryButton onClick={() => void handleCopy()}>{copied ? "Copied" : "Copy link"}</SecondaryButton>
                <a href={buildClientQuotePageUrl(publicToken ?? "")} target="_blank" rel="noopener noreferrer">
                  <SecondaryButton>Open</SecondaryButton>
                </a>
                <SecondaryButton disabled={revoking} onClick={() => void handleRevoke()}>
                  {revoking ? "Revoking…" : "Revoke"}
                </SecondaryButton>
              </>
            ) : null}
          </div>
        }
      >
        {linkUrl ? (
          <p className="break-all font-mono text-xs text-slate-700" data-testid="client-link-url">
            {linkUrl}
          </p>
        ) : null}
        {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
      </SectionCard>
    </div>
  );
}
