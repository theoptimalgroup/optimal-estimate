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

export function formatWorkLabel(work: WorkLabelSource | null | undefined, index: number): string {
  const productLabel = formatProductLabel(work?.product_name, work?.product_code);
  if (productLabel) return productLabel;

  const scope = cleanRichTextForTextarea(work?.scope ?? "").trim();
  if (scope) {
    return scope.length > SCOPE_TRUNCATE ? `${scope.slice(0, SCOPE_TRUNCATE)}…` : scope;
  }

  return `Work ${index + 1}`;
}

export function formatWorkIndexLabel(index: number): string {
  return `Work ${index + 1}`;
}
