"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EworksButton, EworksInput, EworksLabel, EworksLoadingScreen } from "@/components/eworks-ui";
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

function DetailField({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</dt>
      <dd className="mt-1 text-sm text-gray-900 whitespace-pre-wrap break-words">{value?.trim() ? value : "—"}</dd>
    </div>
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
      <div className="w-full max-w-4xl rounded-lg border border-gray-200 bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-gray-200 px-6 py-4">
          <div>
            <h2 id="rate-rule-detail-title" className="text-lg font-semibold text-gray-900">
              Rate Rule Details
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              {rule.client_name ?? rule.xlsx_client_name ?? "Default client"} ·{" "}
              {rule.trade_name ?? rule.xlsx_trade_name ?? "Default trade"} · v{rule.version}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-900"
          >
            Close
          </button>
        </div>

        <div className="max-h-[70vh] overflow-y-auto px-6 py-5">
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <DetailField label="Client" value={rule.client_name} />
            <DetailField label="Trade" value={rule.trade_name} />
            <DetailField label="Formula Source" value={rule.formula_source} />
            <DetailField label="Status" value={rule.is_active ? "Active" : "Inactive"} />
            <DetailField label="Hourly Rate" value={formatRate(rule.hourly_rate)} />
            <DetailField label="Half Day Rate" value={formatRate(rule.half_day_rate)} />
            <DetailField label="Day Rate" value={formatRate(rule.day_rate)} />
            <DetailField label="Material Markup" value={formatMarkup(rule)} />
            <DetailField label="VAT Rate" value={formatPercent(rule.vat_rate)} />
            <DetailField label="Active From" value={formatDate(rule.active_from)} />
            <DetailField label="Active To" value={formatDate(rule.active_to)} />
            <DetailField label="XLSX Client Name" value={rule.xlsx_client_name} />
            <DetailField label="XLSX Trade Name" value={rule.xlsx_trade_name} />
            <DetailField label="Lookup Priority" value={rule.usage.lookup_priority} />
            <DetailField label="Quotes Using Rule" value={String(rule.usage.quotes_using_version)} />
            <DetailField label="Jobs For Client" value={String(rule.usage.jobs_for_client)} />
            <DetailField label="Hourly Overhead %" value={formatFractionAsPercent(rule.hourly_overhead_pct)} />
            <DetailField label="Daily Overhead %" value={formatFractionAsPercent(rule.daily_overhead_pct)} />
            <DetailField
              label="Daily Overhead (Long Job) %"
              value={formatFractionAsPercent(rule.daily_overhead_long_job_pct)}
            />
            <DetailField label="Client Fee %" value={formatFractionAsPercent(rule.client_fee_pct)} />
            <DetailField label="Direct Hourly Cost" value={formatRate(rule.direct_hourly_cost)} />
            <DetailField label="Direct Daily Cost" value={formatRate(rule.direct_daily_cost)} />
            <DetailField label="Labourer Hourly Cost" value={formatRate(rule.labourer_hourly_cost)} />
            <DetailField label="Labourer Daily Cost" value={formatRate(rule.labourer_daily_cost)} />
            <DetailField label="Minimum Hours" value={rule.minimum_hours ?? "—"} />
            <DetailField label="Minimum Charge" value={formatRate(rule.minimum_charge)} />
            <DetailField label="Approval Threshold" value={formatRate(rule.approval_threshold)} />
            <DetailField
              label="Minimum Margin %"
              value={rule.minimum_margin_percentage ? formatPercent(rule.minimum_margin_percentage) : "—"}
            />
            <DetailField label="Rounding Rule" value={rule.rounding_rule} />
            <DetailField label="Created At" value={formatDate(rule.created_at)} />
          </dl>

          <div className="mt-6">
            <DetailField label="Internal Notes Template" value={rule.internal_notes_template} />
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-200 px-6 py-4">
          <StatusBadge active={rule.is_active} />
          <div className="flex gap-2">
            {rule.is_active ? (
              <EworksButton
                type="button"
                variant="secondary"
                disabled={statusUpdating}
                onClick={() => onStatusChange(false)}
                data-testid="rate-rule-deactivate"
              >
                {statusUpdating ? "Updating…" : "Deactivate"}
              </EworksButton>
            ) : (
              <EworksButton
                type="button"
                disabled={statusUpdating}
                onClick={() => onStatusChange(true)}
                data-testid="rate-rule-activate"
              >
                {statusUpdating ? "Updating…" : "Activate"}
              </EworksButton>
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
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Rate Rules</h1>
          <p className="mt-2 text-sm text-gray-600">
            View labour rates, markups, and pricing rules used across estimates.
          </p>
        </div>
        <EworksButton type="button" variant="secondary" onClick={() => void loadRules()} disabled={loading}>
          Refresh
        </EworksButton>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <EworksLabel>
            Search client
            <EworksInput
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Client or XLSX name"
              data-testid="rate-rules-client-search"
            />
          </EworksLabel>
          <EworksLabel>
            Trade filter
            <EworksInput
              value={tradeName}
              onChange={(event) => {
                setTradeName(event.target.value);
                setOffset(0);
              }}
              placeholder="Trade or XLSX name"
              data-testid="rate-rules-trade-filter"
            />
          </EworksLabel>
          <EworksLabel>
            Formula source
            <select
              value={formulaSource}
              onChange={(event) => {
                setFormulaSource(event.target.value);
                setOffset(0);
              }}
              className="w-full min-h-[44px] rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 shadow-sm focus:border-optimal-orange focus:outline-none focus:ring-2 focus:ring-optimal-orange/30"
              data-testid="rate-rules-formula-filter"
            >
              {FORMULA_SOURCES.map((source) => (
                <option key={source || "all"} value={source}>
                  {source ? source : "All sources"}
                </option>
              ))}
            </select>
          </EworksLabel>
          <div className="flex flex-col justify-end gap-3">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={activeOnly}
                onChange={(event) => {
                  setActiveOnly(event.target.checked);
                  setOffset(0);
                }}
                className="h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-optimal-orange"
                data-testid="rate-rules-active-only"
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
        <EworksLoadingScreen message="Loading rate rules…" />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      ) : rules.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
          <p className="text-sm text-gray-600">No rate rules match your filters.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm" data-testid="rate-rules-table">
              <thead className="bg-gray-50">
                <tr>
                  {[
                    "Client",
                    "Trade",
                    "Formula Source",
                    "Status",
                    "Hourly",
                    "Half Day",
                    "Day",
                    "Material Markup",
                    "VAT",
                    "Active From",
                    "Active To",
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
                {rules.map((rule) => (
                  <tr key={rule.id} data-testid={`rate-rule-row-${rule.id}`}>
                    <td className="px-4 py-3 text-gray-900">
                      {rule.client_name ?? rule.xlsx_client_name ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-900">{rule.trade_name ?? rule.xlsx_trade_name ?? "—"}</td>
                    <td className="px-4 py-3 text-gray-700">{rule.formula_source}</td>
                    <td className="px-4 py-3">
                      <StatusBadge active={rule.is_active} />
                    </td>
                    <td className="px-4 py-3 text-gray-700">{formatRate(rule.hourly_rate)}</td>
                    <td className="px-4 py-3 text-gray-700">{formatRate(rule.half_day_rate)}</td>
                    <td className="px-4 py-3 text-gray-700">{formatRate(rule.day_rate)}</td>
                    <td className="px-4 py-3 text-gray-700">{formatMarkup(rule)}</td>
                    <td className="px-4 py-3 text-gray-700">{formatPercent(rule.vat_rate)}</td>
                    <td className="px-4 py-3 text-gray-700">{formatDate(rule.active_from)}</td>
                    <td className="px-4 py-3 text-gray-700">{formatDate(rule.active_to)}</td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => void openDetail(rule.id)}
                        className="text-sm font-medium text-gray-900 underline-offset-2 hover:underline"
                        data-testid={`rate-rule-view-${rule.id}`}
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-200 px-4 py-3 text-sm text-gray-600">
            <p>
              Showing {offset + 1}–{Math.min(offset + rules.length, total)} of {total}
            </p>
            <div className="flex gap-2">
              <EworksButton
                type="button"
                variant="secondary"
                disabled={!canLoadPrevious || loading}
                onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
              >
                Previous
              </EworksButton>
              <EworksButton
                type="button"
                variant="secondary"
                disabled={!canLoadMore || loading}
                onClick={() => setOffset((current) => current + PAGE_SIZE)}
                data-testid="rate-rules-load-more"
              >
                Next
              </EworksButton>
            </div>
          </div>
        </div>
      )}

      {detailLoading && !selectedRule ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20">
          <EworksLoadingScreen message="Loading details…" />
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
