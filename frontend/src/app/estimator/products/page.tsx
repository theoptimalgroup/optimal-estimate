"use client";

import { useCallback, useEffect, useState } from "react";

import { EworksButton, EworksInput, EworksLabel, EworksLoadingScreen } from "@/components/eworks-ui";
import { listEstimatorProducts, type EstimatorProduct } from "@/lib/estimator";

export default function EstimatorProductsPage() {
  const [products, setProducts] = useState<EstimatorProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  const loadProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listEstimatorProducts(search || undefined);
      setProducts(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load products");
      setProducts([]);
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    void loadProducts();
  }, [loadProducts]);

  return (
    <div className="space-y-6" data-testid="estimator-products-page">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Products / Scope</h1>
          <p className="mt-2 text-sm text-gray-600">Read-only catalogue of active products and scope templates</p>
        </div>
        <EworksButton type="button" onClick={() => void loadProducts()} disabled={loading}>
          Refresh
        </EworksButton>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <EworksLabel htmlFor="products-search">Search</EworksLabel>
        <div className="mt-1 flex gap-2">
          <EworksInput
            id="products-search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Product name, code, category…"
          />
          <EworksButton type="button" onClick={() => setSearch(searchInput.trim())}>
            Search
          </EworksButton>
        </div>
      </div>

      {loading ? (
        <EworksLoadingScreen message="Loading products…" />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : products.length === 0 ? (
        <p className="text-sm text-gray-500">No active products found.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-200 text-sm" data-testid="estimator-products-table">
            <thead className="bg-gray-50">
              <tr>
                {["Product", "Code", "Category", "Scope"].map((header) => (
                  <th key={header} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {products.map((product) => (
                <tr key={product.id}>
                  <td className="px-4 py-3 font-medium text-gray-900">{product.product_name}</td>
                  <td className="px-4 py-3 text-gray-700">{product.product_code || "—"}</td>
                  <td className="px-4 py-3 text-gray-700">{product.category || "—"}</td>
                  <td className="px-4 py-3 text-gray-700">{product.scope_of_work || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
