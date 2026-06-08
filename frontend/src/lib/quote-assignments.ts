import { apiFetch } from "@/lib/api";

export type AssignmentType = "estimator" | "engineer";
export type AssigneeKind = "registered" | "external";
export type AssignmentStatus = "assigned" | "in_progress" | "submitted" | "cancelled";

export type AssigneeUser = {
  id: string;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
};

export type AssignmentQuoteSummary = {
  synced_quote_id: number;
  eworks_quote_id: number;
  quote_ref: string | null;
  customer_name: string | null;
  site_address: string | null;
  quote_date: string | null;
  expiry_date: string | null;
  description: string | null;
  tags: string[];
};

export type QuoteAssignment = {
  id: number;
  synced_quote_id: number;
  eworks_quote_id: number;
  quote_ref: string | null;
  assigned_user_id: string | null;
  assigned_user_email: string | null;
  assigned_user_name: string | null;
  assignment_type: AssignmentType;
  assignee_kind: AssigneeKind;
  status: AssignmentStatus;
  assignment_token?: string | null;
  assignment_token_created_at: string | null;
  assignment_token_expires_at: string | null;
  assignment_token_revoked_at: string | null;
  assigned_by_user_id: string | null;
  assigned_by_email: string | null;
  assigned_at: string | null;
  notes: string | null;
  assignment_link: string | null;
  quote_summary?: AssignmentQuoteSummary | null;
  has_calculation_session?: boolean;
  calculation_session_id?: string | null;
  can_start_estimate?: boolean;
  submitted_at?: string | null;
  final_total?: string | null;
  current_version_number?: number | null;
  revision_in_progress?: boolean;
  active_revision_reason?: string | null;
  can_revise?: boolean;
  can_continue_revision?: boolean;
  can_view_submission?: boolean;
  source?: "manual" | "eworks_appointment" | string | null;
  is_derived?: boolean;
  appointment_start_at?: string | null;
  appointment_end_at?: string | null;
  appointment_status?: string | null;
  appointment_type?: string | null;
  job_ref?: string | null;
};

export type AssignmentStartEstimateResult = {
  session_id: string;
  session_token: string;
  resume_url: string;
  assignment_id: number;
  quote_ref: string | null;
};

export type AssignmentCreatePayload = {
  assignment_type: AssignmentType;
  assignee_kind: AssigneeKind;
  assigned_user_id?: string;
  assigned_user_email?: string;
  assigned_user_name?: string;
  notes?: string;
  expires_at?: string;
};

export type PublicAssignment = {
  assignment_id: number;
  assignment_type: AssignmentType;
  assignee_kind: AssigneeKind;
  status: AssignmentStatus;
  assigned_user_name: string | null;
  assigned_user_email: string | null;
  assigned_by_name: string | null;
  assigned_at: string | null;
  notes: string | null;
  quote_ref: string | null;
  customer_name: string | null;
  site_address: string | null;
  quote_date: string | null;
  expiry_date: string | null;
  description: string | null;
  tags: string[];
};

export async function listAssignees(): Promise<AssigneeUser[]> {
  const resp = await apiFetch<AssigneeUser[]>("/api/v1/quote-assignments/assignees");
  return resp.data;
}

export async function listQuoteAssignments(quoteId: number): Promise<QuoteAssignment[]> {
  const resp = await apiFetch<{ items: QuoteAssignment[]; total: number }>(
    `/api/v1/eworks-sync/quotes/${quoteId}/assignments`,
  );
  return resp.data.items;
}

export async function createQuoteAssignment(
  quoteId: number,
  payload: AssignmentCreatePayload,
): Promise<QuoteAssignment> {
  const resp = await apiFetch<QuoteAssignment>(
    `/api/v1/eworks-sync/quotes/${quoteId}/assignments`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
  return resp.data;
}

export async function revokeQuoteAssignment(assignmentId: number): Promise<QuoteAssignment> {
  const resp = await apiFetch<QuoteAssignment>(
    `/api/v1/quote-assignments/${assignmentId}/revoke`,
    { method: "POST" },
  );
  return resp.data;
}

export async function listMyQuoteAssignments(): Promise<QuoteAssignment[]> {
  const resp = await apiFetch<QuoteAssignment[]>("/api/v1/quote-assignments/my");
  return resp.data;
}

export async function startAssignmentEstimate(
  assignmentId: number,
): Promise<AssignmentStartEstimateResult> {
  const resp = await apiFetch<AssignmentStartEstimateResult>(
    `/api/v1/quote-assignments/${assignmentId}/start-estimate`,
    { method: "POST" },
  );
  return resp.data;
}

export async function getPublicAssignment(token: string): Promise<PublicAssignment> {
  const resp = await apiFetch<PublicAssignment>(
    `/api/v1/quote-assignments/public/${token}`,
    {},
    null,
  );
  return resp.data;
}

export async function startPublicAssignmentEstimate(
  token: string,
): Promise<AssignmentStartEstimateResult> {
  const resp = await apiFetch<AssignmentStartEstimateResult>(
    `/api/v1/quote-assignments/public/${token}/start-estimate`,
    { method: "POST" },
    null,
  );
  return resp.data;
}

export async function submitPublicAssignment(
  token: string,
  notes?: string,
): Promise<PublicAssignment> {
  const resp = await apiFetch<PublicAssignment>(
    `/api/v1/quote-assignments/public/${token}/submit`,
    {
      method: "POST",
      body: JSON.stringify({ notes: notes ?? null }),
    },
    null,
  );
  return resp.data;
}

export function formatAssignmentStatusLabel(status: AssignmentStatus | string): string {
  switch (status) {
    case "assigned":
      return "Assigned";
    case "in_progress":
      return "In Progress";
    case "submitted":
      return "Submitted";
    case "cancelled":
      return "Cancelled";
    default:
      return status.replace(/_/g, " ");
  }
}

export function assignmentStatusTone(
  status: AssignmentStatus | string,
): "warning" | "info" | "success" | "error" | "neutral" {
  switch (status) {
    case "assigned":
      return "warning";
    case "in_progress":
      return "info";
    case "submitted":
      return "success";
    case "cancelled":
      return "error";
    default:
      return "neutral";
  }
}

export function formatAssignedAt(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(date);
}

export function buildAssignmentLink(link: string | null | undefined): string {
  if (!link) return "";
  if (link.startsWith("http")) return link;
  if (typeof window !== "undefined") {
    return `${window.location.origin}${link.startsWith("/") ? link : `/${link}`}`;
  }
  return link;
}
