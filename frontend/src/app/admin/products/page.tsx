"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EworksInput, EworksLabel } from "@/components/eworks-ui";
import {
  BackLink,
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableRow,
  DateText,
  EmptyState,
  ErrorState,
  FilterBar,
  FilterField,
  LoadingState,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionCard,
  StatusBadge,
  activeStatusTone,
  filterInputClass,
} from "@/components/ui";
import {
  formatDate,
  formatProductSyncError,
  getProduct,
  hasScope,
  listProducts,
  syncProductsFromEworks,
  updateProduct,
  type Product,
  type ProductSyncSummary,
  type ProductUpdatePayload,
} from "@/lib/products";

const PAGE_SIZE = 25;

function ScopeBadge({ available }: { available: boolean }) {
  return (
    <StatusBadge tone={available ? "info" : "warning"}>{available ? "Yes" : "Missing"}</StatusBadge>
  );
}

function ProductEditPanel({
  product,
  onClose,
  onSaved,
}: {
  product: Product;
  onClose: () => void;
  onSaved: (product: Product) => void;
}) {
  const [productName, setProductName] = useState(product.product_name);
  const [productCode, setProductCode] = useState(product.product_code ?? "");
  const [category, setCategory] = useState(product.category ?? "");
  const [scopeOfWork, setScopeOfWork] = useState(product.scope_of_work ?? "");
  const [description, setDescription] = useState(product.description ?? "");
  const [isActive, setIsActive] = useState(product.is_active);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!productName.trim()) {
      setError("Product name is required");
      return;
    }
    setSaving(true);
    setError(null);
    const payload: ProductUpdatePayload = {
      product_name: productName.trim(),
      product_code: productCode.trim() || null,
      category: category.trim() || null,
      scope_of_work: scopeOfWork,
      description: description,
      is_active: isActive,
    };
    try {
      const updated = await updateProduct(product.id, payload);
      onSaved(updated);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save product");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="product-edit-title"
      data-testid="product-edit-modal"
    >
      <div className="w-full max-w-3xl rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-6 py-5">
          <BackLink
            href="/admin/products"
            label="Back to Products"
            onClick={(event) => {
              event.preventDefault();
              onClose();
            }}
          />
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 id="product-edit-title" className="text-lg font-semibold text-slate-900">
                Edit Product / Scope
              </h2>
              <p className="mt-1 text-sm text-slate-600">eWorks ID: {product.eworks_item_id}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-2.5 py-1.5 text-sm text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
            >
              Close
            </button>
          </div>
        </div>

        <div className="space-y-5 px-6 py-6">
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}

          <EworksLabel>
            Product Name *
            <EworksInput value={productName} onChange={(event) => setProductName(event.target.value)} />
          </EworksLabel>

          <EworksLabel>
            Product Code
            <EworksInput value={productCode} onChange={(event) => setProductCode(event.target.value)} />
          </EworksLabel>

          <EworksLabel>
            Category / Trade
            <EworksInput
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              placeholder="eWorks category (e.g. Plumber)"
            />
          </EworksLabel>

          <EworksLabel>
            Scope of Work
            <textarea
              value={scopeOfWork}
              onChange={(event) => setScopeOfWork(event.target.value)}
              rows={5}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              data-testid="product-scope-input"
            />
            {!scopeOfWork.trim() ? (
              <p className="mt-1 text-xs text-amber-700">
                Warning: empty scope will not auto-populate the estimate form when this product is selected.
              </p>
            ) : null}
          </EworksLabel>

          <EworksLabel>
            Description
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </EworksLabel>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(event) => setIsActive(event.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            Active (visible in estimate product dropdown)
          </label>

          <dl className="grid gap-3 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Source</dt>
              <dd className="mt-1 text-slate-900">eWorks sync</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Type</dt>
              <dd className="mt-1 text-slate-900">{product.type ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Created</dt>
              <dd className="mt-1 text-slate-900">{formatDate(product.created_at)}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Updated</dt>
              <dd className="mt-1 text-slate-900">{formatDate(product.updated_at)}</dd>
            </div>
          </dl>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-slate-100 px-6 py-5">
          <SecondaryButton onClick={onClose} disabled={saving}>
            Cancel
          </SecondaryButton>
          <PrimaryButton onClick={() => void handleSave()} disabled={saving} data-testid="product-save">
            {saving ? "Saving…" : "Save Changes"}
          </PrimaryButton>
        </div>
      </div>
    </div>
  );
}

function SyncSummaryBanner({ summary }: { summary: ProductSyncSummary }) {
  const hasFailures = summary.failed > 0;
  const previewErrors = summary.errors.slice(0, 3);

  return (
    <div
      className={
        hasFailures
          ? "rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          : "rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900"
      }
      data-testid="products-sync-summary"
    >
      <p className="font-medium">
        {hasFailures
          ? `Sync completed with ${summary.failed} failed item${summary.failed === 1 ? "" : "s"}`
          : "Product sync completed"}
      </p>
      <p className="mt-1">
        Fetched {summary.fetched} · Created {summary.created} · Updated {summary.updated} · Skipped{" "}
        {summary.skipped}
        {summary.failed > 0 ? ` · Failed ${summary.failed}` : ""}
      </p>
      {previewErrors.length > 0 ? (
        <ul className="mt-2 space-y-1 text-xs" data-testid="products-sync-error-list">
          {previewErrors.map((item) => (
            <li key={`${item.eworks_item_id}-${item.error}`}>
              Item {item.eworks_item_id || "unknown"}
              {item.item_name ? ` (${item.item_name})` : ""}: {item.error}
            </li>
          ))}
          {summary.errors.length > previewErrors.length ? (
            <li>…and {summary.errors.length - previewErrors.length} more</li>
          ) : null}
        </ul>
      ) : null}
    </div>
  );
}

export default function AdminProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [lastPage, setLastPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [activeOnly, setActiveOnly] = useState(false);

  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncSummary, setSyncSummary] = useState<ProductSyncSummary | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  const filters = useMemo(
    () => ({
      search: search || undefined,
      category: categoryFilter || undefined,
      active: activeOnly ? true : undefined,
      page,
      perPage: PAGE_SIZE,
    }),
    [search, categoryFilter, activeOnly, page],
  );

  const loadProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listProducts(filters);
      setProducts(result.items);
      setTotal(result.total);
      setLastPage(result.lastPage);
    } catch (err) {
      setProducts([]);
      setTotal(0);
      setError(err instanceof Error ? err.message : "Failed to load products");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void loadProducts();
  }, [loadProducts]);

  const applySearch = () => {
    setSearch(searchInput);
    setPage(1);
  };

  const openEdit = async (productId: number) => {
    setDetailLoading(true);
    setError(null);
    try {
      const product = await getProduct(productId);
      setSelectedProduct(product);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load product details");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSaved = (updated: Product) => {
    setProducts((current) => current.map((item) => (item.id === updated.id ? updated : item)));
  };

  const handleSyncFromEworks = async () => {
    setSyncing(true);
    setSyncError(null);
    setSyncSummary(null);
    try {
      const result = await syncProductsFromEworks();
      setSyncSummary(result.summary);
      await loadProducts();
    } catch (err) {
      setSyncError(formatProductSyncError(err));
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="admin-products-page">
      <PageHeader
        title="Products / Scope"
        description="Manage synced products and scope-of-work templates."
        actions={
          <div className="flex flex-wrap gap-2">
            <PrimaryButton
              onClick={() => void handleSyncFromEworks()}
              disabled={loading || syncing}
              data-testid="products-sync-eworks"
            >
              {syncing ? "Syncing…" : "Sync from eWorks"}
            </PrimaryButton>
            <SecondaryButton onClick={() => void loadProducts()} disabled={loading || syncing}>
              Refresh
            </SecondaryButton>
          </div>
        }
      />

      <p className="text-sm text-slate-600" data-testid="products-sync-helper">
        Read-only from eWorks.
      </p>

      {syncSummary ? <SyncSummaryBanner summary={syncSummary} /> : null}
      {syncError ? (
        <div
          className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
          data-testid="products-sync-error"
        >
          {syncError}
        </div>
      ) : null}

      <FilterBar>
        <FilterField label="Search">
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Name, code, or scope"
            className={filterInputClass}
            data-testid="products-search"
          />
        </FilterField>
        <FilterField label="Category / Trade">
          <input
            value={categoryFilter}
            onChange={(event) => {
              setCategoryFilter(event.target.value);
              setPage(1);
            }}
            placeholder="e.g. Plumber"
            className={filterInputClass}
            data-testid="products-category-filter"
          />
        </FilterField>
        <FilterField label="Filters" className="sm:min-w-[200px]">
          <label className="flex min-h-[40px] items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={activeOnly}
              onChange={(event) => {
                setActiveOnly(event.target.checked);
                setPage(1);
              }}
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              data-testid="products-active-only"
            />
            Active only
          </label>
        </FilterField>
        <div className="flex shrink-0 items-end">
          <PrimaryButton onClick={applySearch}>Apply search</PrimaryButton>
        </div>
      </FilterBar>

      {loading ? (
        <LoadingState message="Loading products…" />
      ) : error ? (
        <ErrorState message={error} />
      ) : products.length === 0 ? (
        <EmptyState title="No products found" description="No products match your filters." />
      ) : (
        <SectionCard padding="none">
          <DataTable testId="products-table" className="rounded-none border-0 shadow-none">
            <DataTableHead>
              {[
                "Product Name",
                "Product Code",
                "Category",
                "Scope Available",
                "Active",
                "eWorks ID",
                "Updated At",
                "Actions",
              ].map((heading) => (
                <DataTableCell key={heading} header>
                  {heading}
                </DataTableCell>
              ))}
            </DataTableHead>
            <DataTableBody>
              {products.map((product) => (
                <DataTableRow key={product.id} data-testid={`product-row-${product.id}`}>
                  <DataTableCell className="font-medium text-slate-900">{product.product_name}</DataTableCell>
                  <DataTableCell>{product.product_code ?? "—"}</DataTableCell>
                  <DataTableCell>{product.category ?? "—"}</DataTableCell>
                  <DataTableCell>
                    <ScopeBadge available={hasScope(product)} />
                  </DataTableCell>
                  <DataTableCell>
                    <StatusBadge tone={activeStatusTone(product.is_active)}>
                      {product.is_active ? "Active" : "Inactive"}
                    </StatusBadge>
                  </DataTableCell>
                  <DataTableCell>{product.eworks_item_id}</DataTableCell>
                  <DataTableCell>
                    <DateText value={product.updated_at} includeTime />
                  </DataTableCell>
                  <DataTableCell>
                    <button
                      type="button"
                      onClick={() => void openEdit(product.id)}
                      className="text-sm font-medium text-blue-600 underline-offset-2 hover:text-blue-700 hover:underline"
                      data-testid={`product-edit-${product.id}`}
                    >
                      View / Edit
                    </button>
                  </DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
            <p>
              Page {page} of {lastPage} · {total} total
            </p>
            <div className="flex gap-2">
              <SecondaryButton
                disabled={page <= 1 || loading}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
              >
                Previous
              </SecondaryButton>
              <SecondaryButton
                disabled={page >= lastPage || loading}
                onClick={() => setPage((current) => current + 1)}
                data-testid="products-load-more"
              >
                Next
              </SecondaryButton>
            </div>
          </div>
        </SectionCard>
      )}

      {detailLoading && !selectedProduct ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20">
          <LoadingState message="Loading product…" />
        </div>
      ) : null}

      {selectedProduct ? (
        <ProductEditPanel
          product={selectedProduct}
          onClose={() => setSelectedProduct(null)}
          onSaved={handleSaved}
        />
      ) : null}
    </div>
  );
}
