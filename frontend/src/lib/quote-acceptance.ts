export type EworksAcceptanceSyncStatus = {
  status: string | null;
  synced_at: string | null;
  error: string | null;
  attempts: number;
};

export type QuoteAcceptanceStatus = {
  accepted: boolean;
  accepted_at: string | null;
  name: string | null;
  email?: string | null;
  notes?: string | null;
  eworks_sync?: EworksAcceptanceSyncStatus;
};

export type PublicQuoteAcceptance = {
  accepted: boolean;
  accepted_at: string | null;
  name: string | null;
};

export function normalizeEworksSync(raw: Record<string, unknown> | null | undefined): EworksAcceptanceSyncStatus {
  const data = raw ?? {};
  return {
    status: data.status != null ? String(data.status) : null,
    synced_at: data.synced_at != null ? String(data.synced_at) : null,
    error: data.error != null ? String(data.error) : null,
    attempts: Number(data.attempts ?? 0),
  };
}

export function normalizeQuoteAcceptance(raw: Record<string, unknown> | null | undefined): QuoteAcceptanceStatus {
  const data = raw ?? {};
  return {
    accepted: Boolean(data.accepted),
    accepted_at: data.accepted_at != null ? String(data.accepted_at) : null,
    name: data.name != null ? String(data.name) : null,
    email: data.email != null ? String(data.email) : null,
    notes: data.notes != null ? String(data.notes) : null,
    eworks_sync: normalizeEworksSync(data.eworks_sync as Record<string, unknown> | undefined),
  };
}

export function normalizePublicAcceptance(raw: Record<string, unknown> | null | undefined): PublicQuoteAcceptance {
  const data = raw ?? {};
  return {
    accepted: Boolean(data.accepted),
    accepted_at: data.accepted_at != null ? String(data.accepted_at) : null,
    name: data.name != null ? String(data.name) : null,
  };
}

export function eworksSyncLabel(status: string | null | undefined): string {
  switch (status) {
    case "success":
      return "Synced to eWorks";
    case "failed":
      return "Sync failed";
    case "skipped":
      return "Sync skipped";
    case "pending":
      return "Sync pending";
    default:
      return "Not synced";
  }
}

export function canRetryEworksSync(acceptance: QuoteAcceptanceStatus): boolean {
  if (!acceptance.accepted) return false;
  const status = acceptance.eworks_sync?.status;
  return status === "failed" || status === "skipped";
}
