"use client";

import { useState } from "react";

import { EworksButton } from "@/components/eworks-ui";
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
    <section
      className="rounded-lg border border-indigo-200 bg-indigo-50 p-4"
      data-testid="client-link-panel"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-gray-900">Client quote link</h2>
          <p className="mt-1 text-sm text-gray-600">
            Generate a secure public link for the client to view this quote without staff login.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <EworksButton type="button" disabled={loading} onClick={() => void handleCreateLink()}>
            {loading ? "Creating…" : linkUrl ? "Refresh link" : "Create client link"}
          </EworksButton>
          {linkUrl ? (
            <>
              <EworksButton type="button" variant="secondary" onClick={() => void handleCopy()}>
                {copied ? "Copied" : "Copy link"}
              </EworksButton>
              <a href={buildClientQuotePageUrl(publicToken ?? "")} target="_blank" rel="noopener noreferrer">
                <EworksButton type="button" variant="secondary">
                  Open
                </EworksButton>
              </a>
              <EworksButton type="button" variant="secondary" disabled={revoking} onClick={() => void handleRevoke()}>
                {revoking ? "Revoking…" : "Revoke"}
              </EworksButton>
            </>
          ) : null}
        </div>
      </div>
      {linkUrl ? (
        <p className="mt-3 break-all font-mono text-xs text-gray-700" data-testid="client-link-url">
          {linkUrl}
        </p>
      ) : null}
      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
    </section>
  );
}
