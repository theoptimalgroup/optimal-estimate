import type { ProductOption } from "@/lib/eworks-calculate-schema";
import { cleanRichTextForTextarea } from "@/lib/html-text";

export type WorkScopeState = {
  scope?: string;
  scope_from_product?: boolean;
  other_notes?: string;
  findings?: string;
};

export function hasManualOrEngineerScope(work: WorkScopeState): boolean {
  const scope = (work.scope ?? "").trim();
  if (!scope) return false;
  if (work.scope_from_product) return false;
  return true;
}

export function shouldPromptScopeReplace(work: WorkScopeState, newScope: string): boolean {
  const currentScope = (work.scope ?? "").trim();
  const trimmedNew = newScope.trim();
  if (!currentScope) return false;
  if (work.scope_from_product) return false;
  if (currentScope === trimmedNew) return false;
  return true;
}

export function canAutoFillScope(work: WorkScopeState): boolean {
  const currentScope = (work.scope ?? "").trim();
  return !currentScope || Boolean(work.scope_from_product);
}

export function productScopeText(product: ProductOption | null | undefined): string {
  return cleanRichTextForTextarea(product?.scope_of_work);
}

export function hasProductScope(product: ProductOption | null | undefined): boolean {
  return Boolean(productScopeText(product));
}
