"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { EworksFieldError, EworksInput, cn } from "@/components/eworks-ui";
import { formatProductLabel, type ProductOption } from "@/lib/eworks-calculate-schema";
import { stripHtmlFromLabel } from "@/lib/html-text";
import { fetchProducts } from "@/lib/products-api";

type Props = {
  selectedProductId: number | null | undefined;
  productName?: string;
  productCode?: string;
  customScopeLabel?: string | null;
  onSelect: (product: ProductOption | null) => void;
  onAddCustomScope?: () => void;
  disabled?: boolean;
  className?: string;
};

export function ProductCombobox({
  selectedProductId,
  productName,
  productCode,
  customScopeLabel,
  onSelect,
  onAddCustomScope,
  disabled = false,
  className,
}: Props) {
  const listboxId = useId();
  const containerRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [products, setProducts] = useState<ProductOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const customLabel = customScopeLabel?.trim() ? `Custom: ${customScopeLabel.trim()}` : "";
  const selectedLabel =
    customLabel ||
    (productName?.trim()
      ? formatProductLabel({
          product_name: stripHtmlFromLabel(productName),
          product_code: productCode ?? null,
        })
      : "");

  const loadProducts = useCallback(async (search: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchProducts({ search, perPage: 100, page: 1 });
      setProducts(result.data);
    } catch (err) {
      setProducts([]);
      setError(err instanceof Error ? err.message : "Failed to load products");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProducts("");
  }, [loadProducts]);

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => {
      void loadProducts(query);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [open, query, loadProducts]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const displayValue = open ? query : selectedLabel;

  return (
    <div ref={containerRef} className={cn("relative min-w-0 flex-1", className)}>
      <EworksInput
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-autocomplete="list"
        placeholder="Select product…"
        data-testid="product-combobox"
        disabled={disabled}
        value={displayValue}
        onFocus={() => {
          setOpen(true);
          setQuery(selectedLabel);
        }}
        onChange={(e) => {
          setOpen(true);
          setQuery(e.target.value);
        }}
        className="min-h-[40px] w-full text-sm"
      />
      {open && (
        <div
          id={listboxId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg"
        >
          <button
            type="button"
            role="option"
            aria-selected={selectedProductId == null}
            className="block w-full px-3 py-2 text-left text-sm text-slate-600 hover:bg-slate-50"
            onClick={() => {
              onSelect(null);
              setQuery("");
              setOpen(false);
            }}
          >
            No product selected
          </button>
          {loading && <p className="px-3 py-2 text-xs text-optimal-muted">Loading products…</p>}
          {!loading && error && <p className="px-3 py-2 text-xs text-red-600">{error}</p>}
          {!loading && !error && products.length === 0 && (
            <p className="px-3 py-2 text-xs text-optimal-muted">No products found</p>
          )}
          {onAddCustomScope ? (
            <button
              type="button"
              role="option"
              aria-selected={false}
              className="block w-full border-t border-slate-100 px-3 py-2.5 text-left text-sm font-medium text-blue-700 hover:bg-blue-50"
              onClick={() => {
                onAddCustomScope();
                setQuery("");
                setOpen(false);
              }}
              data-testid="product-option-custom-scope"
            >
              Product not listed? Add custom scope
            </button>
          ) : null}
          {!loading &&
            !error &&
            products.map((product) => (
              <button
                key={product.id}
                type="button"
                role="option"
                aria-selected={product.id === selectedProductId}
                data-testid="product-option-existing"
                className={cn(
                  "block w-full px-3 py-2 text-left text-sm hover:bg-slate-50",
                  product.id === selectedProductId && "border border-blue-200 bg-blue-50 font-medium text-blue-700",
                )}
                onClick={() => {
                  onSelect(product);
                  setQuery(formatProductLabel({
                    product_name: stripHtmlFromLabel(product.product_name),
                    product_code: product.product_code ?? null,
                  }));
                  setOpen(false);
                }}
              >
                {formatProductLabel({
                  product_name: stripHtmlFromLabel(product.product_name),
                  product_code: product.product_code ?? null,
                })}
              </button>
            ))}
        </div>
      )}
      {!open && error && products.length === 0 && <EworksFieldError message={error} />}
    </div>
  );
}
