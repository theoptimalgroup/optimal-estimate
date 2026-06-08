import { cleanRichTextForTextarea, stripHtmlFromLabel } from "@/lib/html-text";

export type WorkLabelSource = {
  product_name?: string | null;
  product_code?: string | null;
  scope?: string | null;
  is_custom_scope?: boolean;
  custom_title?: string | null;
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

function resolvedCustomTitle(work: WorkLabelSource | null | undefined): string {
  if (!work?.is_custom_scope) return "";
  return stripHtmlFromLabel(work.custom_title ?? work.product_name);
}

/** Card title in Step 2: product, custom title, short scope preview, or prompt to select. */
export function formatWorkCardTitle(work: WorkLabelSource | null | undefined): string {
  const customTitle = resolvedCustomTitle(work);
  if (customTitle) return customTitle;

  const productLabel = formatProductLabel(work?.product_name, work?.product_code);
  if (productLabel) return productLabel;

  const scope = scopePreview(work?.scope);
  if (scope) return scope;

  return "Select product";
}

/** Validation and internal labels: product, custom title, short scope preview, or neutral fallback. */
export function formatWorkLabel(work: WorkLabelSource | null | undefined): string {
  const customTitle = resolvedCustomTitle(work);
  if (customTitle) return customTitle;

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
