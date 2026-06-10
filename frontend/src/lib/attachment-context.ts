import type { AttachmentMeta, WorkBlockFormValues } from "@/lib/eworks-calculate-schema";
import { stripHtmlFromLabel } from "@/lib/html-text";

const DEFAULT_SCOPE_TRUNCATE = 100;

/** Trim, collapse whitespace, strip HTML, truncate with ellipsis; "Not available" if empty. */
export function formatAttachmentContextLabel(
  value: string | null | undefined,
  maxLength = DEFAULT_SCOPE_TRUNCATE,
): string {
  const cleaned = stripHtmlFromLabel(value).replace(/\s+/g, " ").trim();
  if (!cleaned) return "Not available";
  if (cleaned.length <= maxLength) return cleaned;
  return `${cleaned.slice(0, maxLength)}…`;
}

function resolveAttachmentProductName(file: AttachmentMeta, values: WorkBlockFormValues): string | null {
  if (file.is_custom_scope) {
    const title = file.custom_scope_title?.trim() || file.product_name?.trim();
    return title || null;
  }
  const productName = file.product_name?.trim() || values.product_name?.trim();
  return productName || null;
}

function resolveAttachmentScopeLabel(file: AttachmentMeta): string | null {
  const customTitle = file.custom_scope_title?.trim();
  if (customTitle) {
    return formatAttachmentContextLabel(customTitle);
  }

  const workLabel = file.work_block_label?.trim();
  const productName = file.is_custom_scope ? null : file.product_name?.trim();
  const workLabelIsProductOnly =
    workLabel &&
    productName &&
    (workLabel === productName || workLabel.startsWith(`${productName} ·`));
  if (workLabel && !workLabelIsProductOnly) {
    return formatAttachmentContextLabel(workLabel);
  }

  const snapshot = file.scope_snapshot?.trim();
  if (snapshot) {
    return formatAttachmentContextLabel(snapshot);
  }

  if (workLabel) {
    return formatAttachmentContextLabel(workLabel);
  }

  return null;
}

export function formatAttachmentProductLine(
  file: AttachmentMeta,
  values: WorkBlockFormValues,
): string | null {
  if (file.is_custom_scope) {
    const title = resolveAttachmentProductName(file, values);
    return title ? `Custom: ${formatAttachmentContextLabel(title)}` : null;
  }

  const productName = resolveAttachmentProductName(file, values);
  if (productName) {
    return `Product: ${formatAttachmentContextLabel(productName)}`;
  }

  const workLabel = file.work_block_label?.trim();
  if (workLabel) {
    return `Work: ${formatAttachmentContextLabel(workLabel)}`;
  }

  return null;
}

export function formatAttachmentScopeLine(file: AttachmentMeta): string | null {
  const label = resolveAttachmentScopeLabel(file);
  if (!label || label === "Not available") return null;
  return `Scope: ${label}`;
}

export function attachmentMediaContext(file: AttachmentMeta, values: WorkBlockFormValues) {
  return {
    productLine: formatAttachmentProductLine(file, values),
    scopeLine: formatAttachmentScopeLine(file),
  };
}
