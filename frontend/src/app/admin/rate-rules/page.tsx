"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import {
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
  filterSelectClass,
} from "@/components/ui";
import {
  formatDate,
  formatFractionAsPercent,
  formatMarkup,
  formatPercent,
  formatRate,
  getRateRule,
  listRateRules,
  updateRateRuleStatus,
  type RateRule,
  type RateRuleDetail,
} from "@/lib/rate-rules";

const FORMULA_SOURCES = ["", "simplified", "xlsx"] as const;
const PAGE_SIZE = 25;

const CALCULATION_METHOD_HELP = {
  xlsx: "Uses the Excel-parity calculation engine",
  simplified: "Uses the legacy simplified engine",
} as const;

function formatCalculationMethod(source: string | null | undefined): string {
  if (!source) return "—";
  return source;
}

function DetailField({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-900">{value?.trim() ? value : "—"}</dd>
    </div>
  );
}

function DetailSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-4">
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{children}</dl>
    </section>
  );
}

function RateRuleDetailPanel({
  rule,
  onClose,
  onStatusChange,
  statusUpdating,
}: {
  rule: RateRuleDetail;
  onClose: () => void;
  onStatusChange: (active: boolean) => void;
  statusUpdating: boolean;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="rate-rule-detail-title"
      data-testid="rate-rule-detail-modal"
    >
      <div className="w-full max-w-4xl rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
          <div>
            <h2 id="rate-rule-detail-title" className="text-lg font-semibold text-slate-900">
              Rate Rule Details
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              {rule.client_name ?? rule.xlsx_client_name ?? "Default client"} ·{" "}
              {rule.trade_name ?? rule.xlsx_trade_name ?? "Default trade"} · v{rule.version}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2.5 py-1.5 text-sm text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
          >
            Close
          </button>
        </div>

        <div className="max-h-[70vh] overflow-y-auto px-6 py-6 space-y-8">
          <DetailSection title="Client & Trade">
            <DetailField label="Client" value={rule.client_name} />
            <DetailField label="Trade" value={rule.trade_name} />
            <DetailField label="XLSX Client Name" value={rule.xlsx_client_name} />
            <DetailField label="XLSX Trade Name" value={rule.xlsx_trade_name} />
            <DetailField label="Lookup Priority" value={rule.usage.lookup_priority} />
            <DetailField label="Quotes Using Rule" value={String(rule.usage.quotes_using_version)} />
            <DetailField label="Jobs For Client" value={String(rule.usage.jobs_for_client)} />
            <DetailField label="Status" value={rule.is_active ? "Active" : "Inactive"} />
          </DetailSection>

          <DetailSection title="Pricing Inputs">
            <DetailField label="Client hourly rate" value={formatRate(rule.hourly_rate)} />
            <DetailField label="Direct half-day cost" value={formatRate(rule.half_day_rate)} />
            <DetailField label="Direct day cost" value={formatRate(rule.day_rate)} />
            <DetailField label="Material formula %" value={formatMarkup(rule)} />
            <DetailField label="Direct hourly cost" value={formatRate(rule.direct_hourly_cost)} />
            <DetailField label="Direct daily cost" value={formatRate(rule.direct_daily_cost)} />
            <DetailField label="Labourer hourly cost" value={formatRate(rule.labourer_hourly_cost)} />
            <DetailField label="Labourer daily cost" value={formatRate(rule.labourer_daily_cost)} />
            <DetailField label="Minimum hours" value={rule.minimum_hours ?? "—"} />
            <DetailField label="Minimum charge" value={formatRate(rule.minimum_charge)} />
            <DetailField label="Approval threshold" value={formatRate(rule.approval_threshold)} />
            <DetailField
              label="Minimum margin %"
              value={rule.minimum_margin_percentage ? formatPercent(rule.minimum_margin_percentage) : "—"}
            />
            <DetailField label="Client fee %" value={formatFractionAsPercent(rule.client_fee_pct)} />
            <DetailField label="Hourly overhead %" value={formatFractionAsPercent(rule.hourly_overhead_pct)} />
            <DetailField label="Daily overhead %" value={formatFractionAsPercent(rule.daily_overhead_pct)} />
            <DetailField
              label="Daily overhead (long job) %"
              value={formatFractionAsPercent(rule.daily_overhead_long_job_pct)}
            />
          </DetailSection>

          <DetailSection title="Formula Settings">
            <div className="sm:col-span-2 lg:col-span-3">
              <DetailField label="Calculation method" value={formatCalculationMethod(rule.formula_source)} />
              <p className="mt-2 text-xs text-slate-600">
                <span className="font-medium text-slate-700">xlsx</span> — {CALCULATION_METHOD_HELP.xlsx}.{" "}
                <span className="font-medium text-slate-700">simplified</span> — {CALCULATION_METHOD_HELP.simplified}.
              </p>
            </div>
            <DetailField label="Rounding rule" value={rule.rounding_rule} />
            <DetailField
              label="Material charge denominator"
              value={formatFractionAsPercent(rule.material_charge_denominator)}
            />
            <DetailField
              label="Parking charge denominator"
              value={formatFractionAsPercent(rule.parking_charge_denominator)}
            />
            <DetailField
              label="Congestion charge denominator"
              value={formatFractionAsPercent(rule.congestion_charge_denominator)}
            />
            <DetailField label="MROUND increment" value={formatRate(rule.mround_increment)} />
            <DetailField label="OJ uplift %" value={formatPercent(rule.oj_uplift_pct)} />
            <DetailField label="NHS overhead uplift %" value={formatPercent(rule.nhs_overhead_uplift_pct)} />
            <DetailField label="EAF flat fee" value={formatRate(rule.eaf_flat_fee)} />
          </DetailSection>

          <DetailSection title="VAT & Active Dates">
            <DetailField label="VAT rate" value={formatPercent(rule.vat_rate)} />
            <DetailField label="Active from" value={formatDate(rule.active_from)} />
            <DetailField label="Active to" value={formatDate(rule.active_to)} />
            <DetailField label="Version" value={rule.version} />
            <DetailField label="Created at" value={formatDate(rule.created_at)} />
          </DetailSection>

          <div>
            <DetailField label="Internal notes template" value={rule.internal_notes_template} />
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-6 py-5">
          <StatusBadge tone={activeStatusTone(rule.is_active)}>
            {rule.is_active ? "Active" : "Inactive"}
          </StatusBadge>
          <div className="flex gap-2">
            {rule.is_active ? (
              <SecondaryButton
                disabled={statusUpdating}
                onClick={() => onStatusChange(false)}
                data-testid="rate-rule-deactivate"
              >
                {statusUpdating ? "Updating…" : "Deactivate"}
              </SecondaryButton>
            ) : (
              <PrimaryButton
                disabled={statusUpdating}
                onClick={() => onStatusChange(true)}
                data-testid="rate-rule-activate"
              >
                {statusUpdating ? "Updating…" : "Activate"}
              </PrimaryButton>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AdminRateRulesPage() {
  const [rules, setRules] = useState<RateRule[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [clientName, setClientName] = useState("");
  const [tradeName, setTradeName] = useState("");
  const [formulaSource, setFormulaSource] = useState("");
  const [activeOnly, setActiveOnly] = useState(false);
  const [searchInput, setSearchInput] = useState("");

  const [selectedRule, setSelectedRule] = useState<RateRuleDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [statusUpdating, setStatusUpdating] = useState(false);

  const filters = useMemo(
    () => ({
      client_name: clientName || undefined,
      trade_name: tradeName || undefined,
      formula_source: formulaSource || undefined,
      active: activeOnly ? true : undefined,
      limit: PAGE_SIZE,
      offset,
    }),
    [clientName, tradeName, formulaSource, activeOnly, offset],
  );

  const loadRules = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listRateRules(filters);
      setRules(result.items);
      setTotal(result.total);
    } catch (err) {
      setRules([]);
      setTotal(0);
      setError(err instanceof Error ? err.message : "Failed to load rate rules");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void loadRules();
  }, [loadRules]);

  const applySearch = () => {
    setClientName(searchInput);
    setOffset(0);
  };

  const openDetail = async (ruleId: string) => {
    setDetailLoading(true);
    setError(null);
    try {
      const detail = await getRateRule(ruleId);
      setSelectedRule(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load rate rule details");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleStatusChange = async (active: boolean) => {
    if (!selectedRule) return;
    setStatusUpdating(true);
    setError(null);
    try {
      const updated = await updateRateRuleStatus(selectedRule.id, active);
      setSelectedRule(updated);
      await loadRules();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update rate rule status");
    } finally {
      setStatusUpdating(false);
    }
  };

  const canLoadMore = offset + PAGE_SIZE < total;
  const canLoadPrevious = offset > 0;

  return (
    <div className="space-y-6" data-testid="admin-rate-rules-page">
      <PageHeader
        title="Rate Rules"
        description="View Excel pricing inputs stored per client and trade. Final quote totals are calculated by the backend engine."
        actions={
          <SecondaryButton onClick={() => void loadRules()} disabled={loading}>
            Refresh
          </SecondaryButton>
        }
      />

      <div
        className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-4 text-sm text-blue-900"
        data-testid="rate-rules-info-panel"
      >
        <h2 className="font-semibold text-blue-950">Excel Pricing Inputs</h2>
        <p className="mt-1 leading-relaxed text-blue-900/90">
          These values are imported from the Quote Calculator workbook and stored per Client + Trade. The database
          stores pricing inputs only. Final labour, materials, VAT, profit, discount, and quote totals are calculated
          by the backend calculation engine.
        </p>
      </div>

      <FilterBar>
        <FilterField label="Search client">
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Client or XLSX name"
            className={filterInputClass}
            data-testid="rate-rules-client-search"
          />
        </FilterField>
        <FilterField label="Trade filter">
          <input
            value={tradeName}
            onChange={(event) => {
              setTradeName(event.target.value);
              setOffset(0);
            }}
            placeholder="Trade or XLSX name"
            className={filterInputClass}
            data-testid="rate-rules-trade-filter"
          />
        </FilterField>
        <FilterField label="Calculation method">
          <select
            value={formulaSource}
            onChange={(event) => {
              setFormulaSource(event.target.value);
              setOffset(0);
            }}
            className={filterSelectClass}
            data-testid="rate-rules-formula-filter"
          >
            {FORMULA_SOURCES.map((source) => (
              <option key={source || "all"} value={source}>
                {source ? source : "All methods"}
              </option>
            ))}
          </select>
          <p className="mt-1.5 text-xs leading-relaxed text-slate-500">
            <span className="font-medium text-slate-600">xlsx</span> — {CALCULATION_METHOD_HELP.xlsx}.{" "}
            <span className="font-medium text-slate-600">simplified</span> — {CALCULATION_METHOD_HELP.simplified}.
          </p>
        </FilterField>
        <FilterField label="Filters" className="sm:min-w-[160px]">
          <label className="flex min-h-[40px] items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={activeOnly}
              onChange={(event) => {
                setActiveOnly(event.target.checked);
                setOffset(0);
              }}
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              data-testid="rate-rules-active-only"
            />
            Active only
          </label>
        </FilterField>
        <div className="flex shrink-0 items-end">
          <PrimaryButton onClick={applySearch}>Apply search</PrimaryButton>
        </div>
      </FilterBar>

      {loading ? (
        <LoadingState message="Loading rate rules…" />
      ) : error ? (
        <ErrorState message={error} />
      ) : rules.length === 0 ? (
        <EmptyState title="No rate rules found" description="No rate rules match your filters." />
      ) : (
        <SectionCard padding="none">
          <DataTable testId="rate-rules-table" className="rounded-none border-0 shadow-none">
            <DataTableHead>
              {[
                "Client",
                "Trade",
                "Calculation method",
                "Status",
                "Client hourly rate",
                "Direct half-day cost",
                "Direct day cost",
                "Material formula %",
                "VAT",
                "Active From",
                "Active To",
                "Actions",
              ].map((heading) => (
                <DataTableCell key={heading} header>
                  {heading}
                </DataTableCell>
              ))}
            </DataTableHead>
            <DataTableBody>
              {rules.map((rule) => (
                <DataTableRow key={rule.id} data-testid={`rate-rule-row-${rule.id}`}>
                  <DataTableCell className="text-slate-900">
                    {rule.client_name ?? rule.xlsx_client_name ?? "—"}
                  </DataTableCell>
                  <DataTableCell className="text-slate-900">
                    {rule.trade_name ?? rule.xlsx_trade_name ?? "—"}
                  </DataTableCell>
                  <DataTableCell>{rule.formula_source}</DataTableCell>
                  <DataTableCell>
                    <StatusBadge tone={activeStatusTone(rule.is_active)}>
                      {rule.is_active ? "Active" : "Inactive"}
                    </StatusBadge>
                  </DataTableCell>
                  <DataTableCell>{formatRate(rule.hourly_rate)}</DataTableCell>
                  <DataTableCell>{formatRate(rule.half_day_rate)}</DataTableCell>
                  <DataTableCell>{formatRate(rule.day_rate)}</DataTableCell>
                  <DataTableCell>{formatMarkup(rule)}</DataTableCell>
                  <DataTableCell>{formatPercent(rule.vat_rate)}</DataTableCell>
                  <DataTableCell>
                    <DateText value={rule.active_from} />
                  </DataTableCell>
                  <DataTableCell>
                    <DateText value={rule.active_to} />
                  </DataTableCell>
                  <DataTableCell>
                    <button
                      type="button"
                      onClick={() => void openDetail(rule.id)}
                      className="text-sm font-medium text-blue-600 underline-offset-2 hover:text-blue-700 hover:underline"
                      data-testid={`rate-rule-view-${rule.id}`}
                    >
                      View Details
                    </button>
                  </DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
            <p>
              Showing {offset + 1}–{Math.min(offset + rules.length, total)} of {total}
            </p>
            <div className="flex gap-2">
              <SecondaryButton
                disabled={!canLoadPrevious || loading}
                onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
              >
                Previous
              </SecondaryButton>
              <SecondaryButton
                disabled={!canLoadMore || loading}
                onClick={() => setOffset((current) => current + PAGE_SIZE)}
                data-testid="rate-rules-load-more"
              >
                Next
              </SecondaryButton>
            </div>
          </div>
        </SectionCard>
      )}

      {detailLoading && !selectedRule ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20">
          <LoadingState message="Loading details…" />
        </div>
      ) : null}

      {selectedRule ? (
        <RateRuleDetailPanel
          rule={selectedRule}
          onClose={() => setSelectedRule(null)}
          onStatusChange={(active) => void handleStatusChange(active)}
          statusUpdating={statusUpdating}
        />
      ) : null}
    </div>
  );
}
