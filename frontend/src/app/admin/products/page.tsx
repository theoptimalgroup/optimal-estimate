"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EworksButton, EworksInput, EworksLabel, EworksLoadingScreen } from "@/components/eworks-ui";
import {
  formatDate,
  getProduct,
  hasScope,
  listProducts,
  updateProduct,
  type Product,
  type ProductUpdatePayload,
} from "@/lib/products";

const PAGE_SIZE = 25;

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={
        active
          ? "inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800"
          : "inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700"
      }
    >
      {active ? "Active" : "Inactive"}
    </span>
  );
}

function ScopeBadge({ available }: { available: boolean }) {
  return (
    <span
      className={
        available
          ? "inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800"
          : "inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
      }
    >
      {available ? "Yes" : "Missing"}
    </span>
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
      <div className="w-full max-w-3xl rounded-lg border border-gray-200 bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-gray-200 px-6 py-4">
          <div>
            <h2 id="product-edit-title" className="text-lg font-semibold text-gray-900">
              Edit Product / Scope
            </h2>
            <p className="mt-1 text-sm text-gray-600">eWorks ID: {product.eworks_item_id}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-900"
          >
            Close
          </button>
        </div>

        <div className="space-y-4 px-6 py-5">
          {error ? <p className="text-sm text-red-600">{error}</p> : null}

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
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 shadow-sm focus:border-optimal-orange focus:outline-none focus:ring-2 focus:ring-optimal-orange/30"
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
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 shadow-sm focus:border-optimal-orange focus:outline-none focus:ring-2 focus:ring-optimal-orange/30"
            />
          </EworksLabel>

          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(event) => setIsActive(event.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-optimal-orange"
            />
            Active (visible in estimate product dropdown)
          </label>

          <dl className="grid gap-3 rounded-lg bg-gray-50 p-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Source</dt>
              <dd className="mt-1 text-gray-900">eWorks sync</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Type</dt>
              <dd className="mt-1 text-gray-900">{product.type ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Created</dt>
              <dd className="mt-1 text-gray-900">{formatDate(product.created_at)}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Updated</dt>
              <dd className="mt-1 text-gray-900">{formatDate(product.updated_at)}</dd>
            </div>
          </dl>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-gray-200 px-6 py-4">
          <EworksButton type="button" variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </EworksButton>
          <EworksButton type="button" onClick={() => void handleSave()} disabled={saving} data-testid="product-save">
            {saving ? "Saving…" : "Save Changes"}
          </EworksButton>
        </div>
      </div>
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

  return (
    <div className="space-y-6" data-testid="admin-products-page">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Products / Scope</h1>
          <p className="mt-2 text-sm text-gray-600">
            Manage product catalogue and scope-of-work templates used in the estimate form.
          </p>
        </div>
        <EworksButton type="button" variant="secondary" onClick={() => void loadProducts()} disabled={loading}>
          Refresh
        </EworksButton>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <EworksLabel>
            Search
            <EworksInput
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Name, code, or scope"
              data-testid="products-search"
            />
          </EworksLabel>
          <EworksLabel>
            Category / Trade
            <EworksInput
              value={categoryFilter}
              onChange={(event) => {
                setCategoryFilter(event.target.value);
                setPage(1);
              }}
              placeholder="e.g. Plumber"
              data-testid="products-category-filter"
            />
          </EworksLabel>
          <div className="flex flex-col justify-end gap-3 lg:col-span-2">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={activeOnly}
                onChange={(event) => {
                  setActiveOnly(event.target.checked);
                  setPage(1);
                }}
                className="h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-optimal-orange"
                data-testid="products-active-only"
              />
              Active only
            </label>
            <EworksButton type="button" onClick={applySearch}>
              Apply search
            </EworksButton>
          </div>
        </div>
      </div>

      {loading ? (
        <EworksLoadingScreen message="Loading products…" />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      ) : products.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
          <p className="text-sm text-gray-600">No products match your filters.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm" data-testid="products-table">
              <thead className="bg-gray-50">
                <tr>
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
                    <th
                      key={heading}
                      scope="col"
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                    >
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {products.map((product) => (
                  <tr key={product.id} data-testid={`product-row-${product.id}`}>
                    <td className="px-4 py-3 font-medium text-gray-900">{product.product_name}</td>
                    <td className="px-4 py-3 text-gray-700">{product.product_code ?? "—"}</td>
                    <td className="px-4 py-3 text-gray-700">{product.category ?? "—"}</td>
                    <td className="px-4 py-3">
                      <ScopeBadge available={hasScope(product)} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge active={product.is_active} />
                    </td>
                    <td className="px-4 py-3 text-gray-700">{product.eworks_item_id}</td>
                    <td className="px-4 py-3 text-gray-700">{formatDate(product.updated_at)}</td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => void openEdit(product.id)}
                        className="text-sm font-medium text-gray-900 underline-offset-2 hover:underline"
                        data-testid={`product-edit-${product.id}`}
                      >
                        View / Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-200 px-4 py-3 text-sm text-gray-600">
            <p>
              Page {page} of {lastPage} · {total} total
            </p>
            <div className="flex gap-2">
              <EworksButton
                type="button"
                variant="secondary"
                disabled={page <= 1 || loading}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
              >
                Previous
              </EworksButton>
              <EworksButton
                type="button"
                variant="secondary"
                disabled={page >= lastPage || loading}
                onClick={() => setPage((current) => current + 1)}
                data-testid="products-load-more"
              >
                Next
              </EworksButton>
            </div>
          </div>
        </div>
      )}

      {detailLoading && !selectedProduct ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20">
          <EworksLoadingScreen message="Loading product…" />
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
