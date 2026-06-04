import { apiFetch } from "@/lib/api";
import type { ProductOption } from "@/lib/eworks-calculate-schema";

type ProductsListMeta = {
  total: number;
  page: number;
  per_page: number;
  last_page: number;
};

type ProductsListResponse = {
  data: ProductOption[];
  meta: ProductsListMeta;
};

function normalizeProduct(raw: Record<string, unknown>): ProductOption {
  return {
    id: Number(raw.id),
    eworks_item_id: Number(raw.eworks_item_id),
    product_name: String(raw.product_name ?? ""),
    product_code: raw.product_code != null ? String(raw.product_code) : null,
    scope_of_work: raw.scope_of_work != null ? String(raw.scope_of_work) : null,
    selling_price: Number(raw.selling_price ?? 0),
    category: raw.category != null ? String(raw.category) : null,
    type: raw.type != null ? String(raw.type) : null,
  };
}

export async function fetchProducts(params?: {
  search?: string;
  page?: number;
  perPage?: number;
  category?: string;
  hasScopeOfWork?: boolean;
}): Promise<ProductsListResponse> {
  const query = new URLSearchParams();
  if (params?.search?.trim()) query.set("search", params.search.trim());
  if (params?.page) query.set("page", String(params.page));
  if (params?.perPage) query.set("per_page", String(params.perPage));
  if (params?.category) query.set("category", params.category);
  if (params?.hasScopeOfWork != null) query.set("has_scope_of_work", String(params.hasScopeOfWork));
  query.set("active", "true");

  const suffix = query.toString() ? `?${query.toString()}` : "";
  const response = await apiFetch<ProductOption[]>(`/api/v1/products${suffix}`);
  return {
    data: (response.data ?? []).map((item) => normalizeProduct(item as unknown as Record<string, unknown>)),
    meta: (response.meta ?? { total: 0, page: 1, per_page: 25, last_page: 1 }) as ProductsListMeta,
  };
}

export async function fetchProduct(id: number): Promise<ProductOption> {
  const response = await apiFetch<ProductOption>(`/api/v1/products/${id}`);
  return normalizeProduct(response.data as unknown as Record<string, unknown>);
}
