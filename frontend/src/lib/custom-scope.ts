import type { WorkBlockFormValues } from "@/lib/eworks-calculate-schema";

export function hasCustomScopeContent(work: Pick<WorkBlockFormValues, "is_custom_scope" | "custom_title" | "scope">): boolean {
  if (!work.is_custom_scope) return false;
  return Boolean(work.custom_title?.trim() || work.scope?.trim());
}

export function hasMaterialOrLabourData(
  work: Pick<
    WorkBlockFormValues,
    | "materials_to_order"
    | "shelf_materials_rows"
    | "engineers_required"
    | "engineers_needed"
    | "labour_required"
    | "labour_needed"
  >,
): boolean {
  const hasSupplierMaterial = work.materials_to_order.some((supplier) =>
    supplier.links.some((link) => link.link?.trim() && Number(link.cost) > 0),
  );
  const hasShelfMaterial = work.shelf_materials_rows.some((row) => row.link?.trim() && Number(row.cost) > 0);
  const hasLabour =
    (work.engineers_required && Number(work.engineers_needed) > 0) ||
    (work.labour_required && Number(work.labour_needed) > 0);
  return hasSupplierMaterial || hasShelfMaterial || hasLabour;
}

export function shouldConfirmSwitchToCustom(
  work: Pick<
    WorkBlockFormValues,
    | "selected_product_id"
    | "scope"
    | "scope_from_product"
    | "materials_to_order"
    | "shelf_materials_rows"
    | "labour_required"
    | "labour_needed"
  >,
): boolean {
  if (work.selected_product_id != null) return true;
  if ((work.scope ?? "").trim()) return true;
  const hasSupplierMaterial = work.materials_to_order.some((supplier) =>
    supplier.links.some((link) => link.link?.trim() && Number(link.cost) > 0),
  );
  const hasShelfMaterial = work.shelf_materials_rows.some((row) => row.link?.trim() && Number(row.cost) > 0);
  const hasConfiguredLabour = work.labour_required && Number(work.labour_needed) > 0;
  return hasSupplierMaterial || hasShelfMaterial || hasConfiguredLabour;
}

export function shouldConfirmSwitchToProduct(
  work: Pick<WorkBlockFormValues, "is_custom_scope" | "custom_title" | "scope" | "findings" | "other_notes">,
): boolean {
  if (!work.is_custom_scope) return false;
  return Boolean(
    work.custom_title?.trim() || work.scope?.trim() || work.findings?.trim() || work.other_notes?.trim(),
  );
}

export function isWorkBlockProductComplete(
  work: Pick<WorkBlockFormValues, "selected_product_id" | "is_custom_scope" | "custom_title" | "scope">,
): boolean {
  if (work.selected_product_id != null) return true;
  if (work.is_custom_scope) {
    return Boolean(work.custom_title?.trim() && work.scope?.trim());
  }
  return false;
}
