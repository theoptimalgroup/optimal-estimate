"use client";

import { useCallback, useEffect, useState } from "react";

import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableRow,
  EmptyState,
  ErrorState,
  FilterBar,
  FilterField,
  filterInputClass,
  LoadingState,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionCard,
} from "@/components/ui";
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
      <PageHeader
        title="Products / Scope"
        description="Read-only catalogue of active products and scope templates"
        actions={
          <SecondaryButton onClick={() => void loadProducts()} disabled={loading}>
            Refresh
          </SecondaryButton>
        }
      />

      <FilterBar>
        <FilterField label="Search" className="min-w-[200px] flex-[2]">
          <input
            id="products-search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Product name, code, category…"
            className={filterInputClass}
          />
        </FilterField>
        <div className="flex gap-2 sm:pb-0.5">
          <PrimaryButton onClick={() => setSearch(searchInput.trim())}>Search</PrimaryButton>
        </div>
      </FilterBar>

      {loading ? (
        <LoadingState message="Loading products…" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void loadProducts()} />
      ) : products.length === 0 ? (
        <EmptyState title="No products" description="No active products found." />
      ) : (
        <SectionCard padding="none">
          <DataTable testId="estimator-products-table">
            <DataTableHead>
              <DataTableCell header>Product</DataTableCell>
              <DataTableCell header>Code</DataTableCell>
              <DataTableCell header>Category</DataTableCell>
              <DataTableCell header>Scope</DataTableCell>
            </DataTableHead>
            <DataTableBody>
              {products.map((product) => (
                <DataTableRow key={product.id}>
                  <DataTableCell className="font-medium text-slate-900">{product.product_name}</DataTableCell>
                  <DataTableCell>{product.product_code || "—"}</DataTableCell>
                  <DataTableCell>{product.category || "—"}</DataTableCell>
                  <DataTableCell>{product.scope_of_work || "—"}</DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>
        </SectionCard>
      )}
    </div>
  );
}
