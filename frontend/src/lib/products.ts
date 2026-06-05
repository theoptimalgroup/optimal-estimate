import { apiFetch } from "@/lib/api";

export type Product = {
  id: number;
  eworks_item_id: number;
  product_name: string;
  product_code: string | null;
  scope_of_work: string | null;
  description: string | null;
  category: string | null;
  type: string | null;
  is_active: boolean;
  selling_price: string | number;
  created_at: string | null;
  updated_at: string | null;
  eworks_created_on: string | null;
  eworks_last_updated_on: string | null;
};

export type ProductListFilters = {
  search?: string;
  category?: string;
  active?: boolean;
  hasScopeOfWork?: boolean;
  page?: number;
  perPage?: number;
};

export type ProductListResult = {
  items: Product[];
  total: number;
  page: number;
  perPage: number;
  lastPage: number;
};

export type ProductUpdatePayload = {
  product_name?: string;
  product_code?: string | null;
  category?: string | null;
  scope_of_work?: string | null;
  description?: string | null;
  is_active?: boolean;
};

export type ProductSyncItemError = {
  eworks_item_id: string;
  item_name: string;
  error: string;
};

export type ProductSyncSummary = {
  fetched: number;
  created: number;
  updated: number;
  skipped: number;
  failed: number;
  errors: ProductSyncItemError[];
};

export type ProductSyncResult = {
  message: string;
  summary: ProductSyncSummary;
};

function normalizeProduct(raw: Record<string, unknown>): Product {
  return {
    id: Number(raw.id),
    eworks_item_id: Number(raw.eworks_item_id),
    product_name: String(raw.product_name ?? ""),
    product_code: raw.product_code != null ? String(raw.product_code) : null,
    scope_of_work: raw.scope_of_work != null ? String(raw.scope_of_work) : null,
    description: raw.description != null ? String(raw.description) : null,
    category: raw.category != null ? String(raw.category) : null,
    type: raw.type != null ? String(raw.type) : null,
    is_active: raw.is_active !== false,
    selling_price: raw.selling_price ?? 0,
    created_at: raw.created_at != null ? String(raw.created_at) : null,
    updated_at: raw.updated_at != null ? String(raw.updated_at) : null,
    eworks_created_on: raw.eworks_created_on != null ? String(raw.eworks_created_on) : null,
    eworks_last_updated_on: raw.eworks_last_updated_on != null ? String(raw.eworks_last_updated_on) : null,
  };
}

function buildQuery(filters: ProductListFilters): string {
  const params = new URLSearchParams();
  if (filters.search?.trim()) params.set("search", filters.search.trim());
  if (filters.category?.trim()) params.set("category", filters.category.trim());
  if (filters.active !== undefined) params.set("active", String(filters.active));
  if (filters.hasScopeOfWork !== undefined) params.set("has_scope_of_work", String(filters.hasScopeOfWork));
  params.set("page", String(filters.page ?? 1));
  params.set("per_page", String(filters.perPage ?? 25));
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function listProducts(filters: ProductListFilters = {}): Promise<ProductListResult> {
  const response = await apiFetch<Product[]>(`/api/v1/products${buildQuery(filters)}`);
  const meta = response.meta ?? {};
  return {
    items: (response.data ?? []).map((item) => normalizeProduct(item as unknown as Record<string, unknown>)),
    total: Number(meta.total ?? 0),
    page: Number(meta.page ?? 1),
    perPage: Number(meta.per_page ?? 25),
    lastPage: Number(meta.last_page ?? 1),
  };
}

export async function getProduct(productId: number): Promise<Product> {
  const response = await apiFetch<Product>(`/api/v1/products/${productId}`);
  return normalizeProduct(response.data as unknown as Record<string, unknown>);
}

export async function updateProduct(productId: number, payload: ProductUpdatePayload): Promise<Product> {
  const response = await apiFetch<Product>(`/api/v1/products/${productId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return normalizeProduct(response.data as unknown as Record<string, unknown>);
}

function normalizeProductSyncError(raw: unknown): ProductSyncItemError {
  if (raw && typeof raw === "object") {
    const item = raw as Record<string, unknown>;
    return {
      eworks_item_id: String(item.eworks_item_id ?? ""),
      item_name: String(item.item_name ?? ""),
      error: String(item.error ?? "invalid item data"),
    };
  }
  return {
    eworks_item_id: "",
    item_name: "",
    error: String(raw ?? "invalid item data"),
  };
}

function normalizeProductSyncSummary(raw: Record<string, unknown>): ProductSyncSummary {
  return {
    fetched: Number(raw.fetched ?? raw.total_fetched ?? 0),
    created: Number(raw.created ?? raw.inserted ?? 0),
    updated: Number(raw.updated ?? 0),
    skipped: Number(raw.skipped ?? 0),
    failed: Number(raw.failed ?? 0),
    errors: Array.isArray(raw.errors) ? raw.errors.map(normalizeProductSyncError) : [],
  };
}

export async function syncProductsFromEworks(): Promise<ProductSyncResult> {
  const response = await apiFetch<ProductSyncResult>("/api/v1/integrations/eworks/products/sync", {
    method: "POST",
  });
  const data = response.data as unknown as Record<string, unknown>;
  const summaryRaw = (data.summary ?? data) as Record<string, unknown>;
  return {
    message: String(data.message ?? "eWorks products synced successfully"),
    summary: normalizeProductSyncSummary(summaryRaw),
  };
}

export function formatProductSyncError(error: unknown): string {
  if (!(error instanceof Error)) {
    return "Failed to sync products from eWorks.";
  }
  const message = error.message;
  if (/EWORKS_(BASE_URL|API_KEY) is missing/i.test(message)) {
    return "eWorks API is not configured. Ask an administrator to set EWORKS_BASE_URL and EWORKS_API_KEY.";
  }
  if (/misconfigured|not configured/i.test(message)) {
    return "eWorks API is not configured. Ask an administrator to set EWORKS_BASE_URL and EWORKS_API_KEY.";
  }
  return message || "Failed to sync products from eWorks.";
}

export function hasScope(product: Product): boolean {
  return Boolean(product.scope_of_work?.trim());
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}
