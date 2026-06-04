import { apiFetch, getApiUrl } from "@/lib/api";
import type { EworksAcceptanceSyncStatus } from "@/lib/quote-acceptance";
import { normalizePublicAcceptance, type PublicQuoteAcceptance } from "@/lib/quote-acceptance";

export type PublicQuoteWork = {
  title: string;
  product_name: string | null;
  scope: string | null;
  description: string | null;
  materials_summary: string | null;
  attachments: Record<string, unknown>[];
};

export type PublicQuoteSummary = {
  work_charges: number;
  materials: number;
  additional_charges: number;
  subtotal: number;
  vat: number;
  total: number;
};

export type PublicClientQuote = {
  quote_ref: string;
  client_name: string;
  trade_name: string;
  status: string;
  scope_of_work: string | null;
  works: PublicQuoteWork[];
  summary: PublicQuoteSummary;
  terms: string | null;
  created_at: string;
  submitted_at: string | null;
  acceptance: PublicQuoteAcceptance;
};

export type PublicQuoteAcceptResult = {
  accepted: boolean;
  already_accepted: boolean;
  accepted_at: string;
  quote_ref: string;
};

export type PublicQuoteLink = {
  public_url: string;
  public_token: string;
  expires_at: string | null;
};

async function publicFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiUrl()}${path}`);
  const payload = await response.json();
  if (!response.ok) {
    const message = payload?.detail?.error?.message || payload?.detail || "Request failed";
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return payload.data as T;
}

function normalizeSummary(raw: Record<string, unknown>): PublicQuoteSummary {
  return {
    work_charges: Number(raw.work_charges ?? 0),
    materials: Number(raw.materials ?? 0),
    additional_charges: Number(raw.additional_charges ?? 0),
    subtotal: Number(raw.subtotal ?? 0),
    vat: Number(raw.vat ?? 0),
    total: Number(raw.total ?? 0),
  };
}

export async function getPublicQuote(publicToken: string): Promise<PublicClientQuote> {
  const raw = await publicFetch<Record<string, unknown>>(`/api/v1/client-quotes/public/${publicToken}`);
  return {
    quote_ref: String(raw.quote_ref ?? ""),
    client_name: String(raw.client_name ?? ""),
    trade_name: String(raw.trade_name ?? ""),
    status: String(raw.status ?? ""),
    scope_of_work: raw.scope_of_work != null ? String(raw.scope_of_work) : null,
    works: ((raw.works as unknown[]) ?? []).map((item) => {
      const work = item as Record<string, unknown>;
      return {
        title: String(work.title ?? ""),
        product_name: work.product_name != null ? String(work.product_name) : null,
        scope: work.scope != null ? String(work.scope) : null,
        description: work.description != null ? String(work.description) : null,
        materials_summary: work.materials_summary != null ? String(work.materials_summary) : null,
        attachments: Array.isArray(work.attachments) ? (work.attachments as Record<string, unknown>[]) : [],
      };
    }),
    summary: normalizeSummary((raw.summary ?? {}) as Record<string, unknown>),
    terms: raw.terms != null ? String(raw.terms) : null,
    created_at: String(raw.created_at ?? ""),
    submitted_at: raw.submitted_at != null ? String(raw.submitted_at) : null,
    acceptance: normalizePublicAcceptance(raw.acceptance as Record<string, unknown> | undefined),
  };
}

export async function acceptPublicQuote(
  publicToken: string,
  payload: { name: string; email: string; notes?: string },
): Promise<PublicQuoteAcceptResult> {
  const response = await fetch(`${getApiUrl()}/api/v1/client-quotes/public/${publicToken}/accept`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) {
    const message = body?.detail?.error?.message || body?.detail || "Failed to accept quote";
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  const data = body.data as Record<string, unknown>;
  return {
    accepted: Boolean(data.accepted),
    already_accepted: Boolean(data.already_accepted),
    accepted_at: String(data.accepted_at ?? ""),
    quote_ref: String(data.quote_ref ?? ""),
  };
}

export function getPublicQuotePdfUrl(publicToken: string): string {
  return `${getApiUrl()}/api/v1/client-quotes/public/${publicToken}/pdf`;
}

export async function createPublicQuoteLink(sessionId: string): Promise<PublicQuoteLink> {
  const response = await apiFetch<PublicQuoteLink>(`/api/v1/client-quotes/${sessionId}/public-link`, {
    method: "POST",
  });
  return {
    public_url: String(response.data.public_url ?? ""),
    public_token: String(response.data.public_token ?? ""),
    expires_at: response.data.expires_at != null ? String(response.data.expires_at) : null,
  };
}

export async function revokePublicQuoteLink(sessionId: string): Promise<void> {
  await apiFetch<{ revoked: boolean }>(`/api/v1/client-quotes/${sessionId}/revoke-public-link`, {
    method: "POST",
  });
}

export async function retryEworksAcceptanceSync(sessionId: string): Promise<EworksAcceptanceSyncStatus> {
  const response = await apiFetch<Record<string, unknown>>(
    `/api/v1/client-quotes/${sessionId}/sync-acceptance-eworks`,
    { method: "POST" },
  );
  const data = (response.data ?? {}) as Record<string, unknown>;
  return {
    status: data.status != null ? String(data.status) : null,
    synced_at: data.synced_at != null ? String(data.synced_at) : null,
    error: data.error != null ? String(data.error) : null,
    attempts: Number(data.attempts ?? 0),
  };
}

export function formatQuoteDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "long" }).format(date);
}

export function formatMoney(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `£${value.toFixed(2)}`;
}

export function buildClientQuotePageUrl(publicToken: string): string {
  return `/client/quote/${publicToken}`;
}

export function buildAbsoluteClientQuoteUrl(publicToken: string): string {
  if (typeof window === "undefined") return buildClientQuotePageUrl(publicToken);
  return `${window.location.origin}${buildClientQuotePageUrl(publicToken)}`;
}
