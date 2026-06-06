import { cleanRichTextForTextarea, stripHtmlFromLabel } from "@/lib/html-text";

export type WorkLabelSource = {
  product_name?: string | null;
  product_code?: string | null;
  scope?: string | null;
};

const SCOPE_TRUNCATE = 60;

export function formatProductLabel(productName?: string | null, productCode?: string | null): string {
  const name = stripHtmlFromLabel(productName);
  if (!name) return "";
  const code = (productCode ?? "").trim();
  return code ? `${name} · ${code}` : name;
}

export function scopePreview(scope?: string | null): string {
  const cleaned = cleanRichTextForTextarea(scope ?? "").trim();
  if (!cleaned) return "";
  return cleaned.length > SCOPE_TRUNCATE ? `${cleaned.slice(0, SCOPE_TRUNCATE)}…` : cleaned;
}

/** Card title in Step 2: product, short scope preview, or prompt to select. */
export function formatWorkCardTitle(work: WorkLabelSource | null | undefined): string {
  const productLabel = formatProductLabel(work?.product_name, work?.product_code);
  if (productLabel) return productLabel;

  const scope = scopePreview(work?.scope);
  if (scope) return scope;

  return "Select product";
}

/** Validation and internal labels: product, short scope preview, or neutral fallback. */
export function formatWorkLabel(work: WorkLabelSource | null | undefined): string {
  const productLabel = formatProductLabel(work?.product_name, work?.product_code);
  if (productLabel) return productLabel;

  const scope = scopePreview(work?.scope);
  if (scope) return scope;

  return "Selected item";
}

export type QuoteSummarySource = {
  trade_name: string;
  quote_number?: string | null;
  works: WorkLabelSource[];
};

const SCOPE_LONG_THRESHOLD = SCOPE_TRUNCATE;

export function isScopeLong(scope?: string | null): boolean {
  const cleaned = cleanRichTextForTextarea(scope ?? "").trim();
  return cleaned.length > SCOPE_LONG_THRESHOLD;
}

/** Manager review summary card: neutral submission title (work names live in Works section). */
export function formatQuoteSummaryTitle(): string {
  return "Submission Summary";
}

export function defaultOpenWorkIndexes(
  works: Array<WorkLabelSource & { work_index: number }>,
): number[] {
  if (works.length !== 1) {
    return [];
  }

  const work = works[0];
  if (isScopeLong(work.scope ?? null)) {
    return [];
  }

  return [work.work_index];
}
