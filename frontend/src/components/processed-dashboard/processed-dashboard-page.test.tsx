import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ProcessedDashboard } from "@/lib/processed-dashboard";

const mockGetProcessedDashboard = vi.fn();
const mockPatchSalesPipeline = vi.fn();

vi.mock("@/lib/processed-dashboard", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/processed-dashboard")>();
  return {
    ...original,
    getProcessedDashboard: (...args: Parameters<typeof original.getProcessedDashboard>) =>
      mockGetProcessedDashboard(...args),
    patchSalesPipeline: (...args: Parameters<typeof original.patchSalesPipeline>) =>
      mockPatchSalesPipeline(...args),
  };
});

import { ProcessedDashboardPage } from "@/components/processed-dashboard/processed-dashboard-page";

function baseQuote(
  overrides: Partial<ProcessedDashboard["categories"]["pending"]["quotes"][0]> = {},
) {
  return {
    id: 1,
    quote_ref: "Q-100",
    eworks_quote_id: 100,
    customer_name: "Acme Ltd",
    site_address: "1 High Street",
    quote_value: 1500,
    processed_at: "2026-06-01T09:00:00Z",
    days_since_processed: 10,
    days_in_current_bucket: 5,
    last_follow_up_at: null,
    next_follow_up_at: "2026-06-05T09:00:00Z",
    follow_up_status: "overdue" as const,
    sales_bucket: "pending" as const,
    sales_note: "Initial note",
    assigned_sales_name: "Alice",
    assigned_sales_email: "alice@example.com",
    assigned_sales_user_id: null,
    eworks_status: "2",
    eworks_status_name: "Processed",
    tags: [],
    quote_detail_link: "/manager/quotes?quote_id=1",
    ...overrides,
  };
}

function buildDashboard(): ProcessedDashboard {
  const pendingQuote = baseQuote();
  const strongQuote = baseQuote({
    id: 2,
    quote_ref: "Q-200",
    eworks_quote_id: 200,
    quote_value: 2500,
    sales_bucket: "strong",
    follow_up_status: "due_today",
    next_follow_up_at: "2026-06-11T09:00:00Z",
    sales_note: null,
  });
  return {
    totals: {
      processed_quotes: 2,
      pipeline_value: 4000,
      strong_value: 2500,
      dormant_quotes: 0,
      overdue_followups: 1,
      due_today_followups: 1,
      no_followup_set: 0,
      average_age_days: 10,
      conversion_rate: 66.7,
      accepted_count: 2,
      rejected_count: 1,
      accepted_value: 5000,
      rejected_value: 500,
    },
    categories: {
      pending: {
        count: 1,
        value: 1500,
        average_age_days: 10,
        overdue_followups: 1,
        quotes: [pendingQuote],
      },
      possible: { count: 0, value: 0, average_age_days: 0, overdue_followups: 0, quotes: [] },
      strong: {
        count: 1,
        value: 2500,
        average_age_days: 8,
        overdue_followups: 0,
        quotes: [strongQuote],
      },
      dormant: { count: 0, value: 0, average_age_days: 0, overdue_followups: 0, quotes: [] },
    },
    aging: {
      "0_7_days": { count: 0, value: 0 },
      "8_14_days": { count: 2, value: 4000 },
      "15_30_days": { count: 0, value: 0 },
      "31_60_days": { count: 0, value: 0 },
      "60_plus_days": { count: 0, value: 0 },
    },
    follow_up_reminders: {
      overdue: [pendingQuote],
      due_today: [strongQuote],
      due_this_week: [],
      no_followup_set: [],
    },
    salesperson_performance: [
      {
        salesperson_name: "Alice",
        salesperson_email: "alice@example.com",
        assigned_count: 2,
        pipeline_value: 4000,
        strong_value: 2500,
        accepted_count: 2,
        rejected_count: 0,
        conversion_rate: 100,
        overdue_followups: 1,
        average_days_to_close: 12,
      },
    ],
    accepted_rejected_trend: [
      {
        month: "2026-06",
        accepted_count: 2,
        rejected_count: 1,
        accepted_value: 5000,
        rejected_value: 500,
      },
    ],
    monthly_pipeline_value: [
      {
        month: "2026-06",
        new_processed_value: 4000,
        active_pipeline_value: 4000,
        strong_pipeline_value: 2500,
        accepted_value: 5000,
        rejected_value: 500,
      },
    ],
  };
}

describe("ProcessedDashboardPage", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    mockGetProcessedDashboard.mockReset();
    mockPatchSalesPipeline.mockReset();
    mockGetProcessedDashboard.mockResolvedValue(buildDashboard());
    mockPatchSalesPipeline.mockResolvedValue(undefined);

    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  async function renderPage() {
    await act(async () => {
      root.render(<ProcessedDashboardPage apiBase="manager" />);
      await Promise.resolve();
    });
  }

  function setFieldValue(element: HTMLInputElement | HTMLTextAreaElement, value: string) {
    const proto =
      element instanceof HTMLTextAreaElement
        ? window.HTMLTextAreaElement.prototype
        : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    setter?.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  }

  it("renders KPI stat cards for admin apiBase", async () => {
    await act(async () => {
      root.render(<ProcessedDashboardPage apiBase="admin" />);
      await Promise.resolve();
    });
    expect(container.querySelector('[data-testid="kpi-processed-quotes"]')?.textContent).toContain("2");
    expect(container.querySelector('[data-testid="kpi-pipeline-value"]')?.textContent).toContain("4,000");
  });

  it("refetches dashboard when Refresh is clicked", async () => {
    await renderPage();
    mockGetProcessedDashboard.mockClear();
    const refreshButton = Array.from(container.querySelectorAll("button")).find((btn) =>
      btn.textContent?.includes("Refresh"),
    );
    await act(async () => {
      refreshButton!.click();
      await Promise.resolve();
    });
    expect(mockGetProcessedDashboard).toHaveBeenCalledWith("manager", undefined);
  });

  it("renders KPI stat cards", async () => {
    await renderPage();
    expect(container.querySelector('[data-testid="kpi-processed-quotes"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="kpi-pipeline-value"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="kpi-strong-value"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="kpi-conversion-rate"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="kpi-overdue"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="kpi-average-age"]')).not.toBeNull();
  });

  it("renders pipeline bucket sections", async () => {
    await renderPage();
    for (const bucket of ["pending", "possible", "strong", "dormant"]) {
      expect(container.querySelector(`[data-testid="pipeline-bucket-${bucket}"]`)).not.toBeNull();
    }
  });

  it("calls patchSalesPipeline when moving a quote bucket", async () => {
    await renderPage();
    const moveButton = Array.from(container.querySelectorAll("button")).find((btn) =>
      btn.textContent?.includes("Strong"),
    );
    expect(moveButton).toBeTruthy();
    await act(async () => {
      moveButton!.click();
      await Promise.resolve();
    });
    expect(mockPatchSalesPipeline).toHaveBeenCalledWith(1, { sales_bucket: "strong" });
  });

  it("calls patchSalesPipeline when saving a sales note", async () => {
    await renderPage();
    const textarea = container.querySelector("textarea") as HTMLTextAreaElement;
    await act(async () => {
      setFieldValue(textarea, "Updated sales note");
    });
    const saveButton = Array.from(container.querySelectorAll("button")).find((btn) =>
      btn.textContent?.includes("Save"),
    );
    await act(async () => {
      saveButton!.click();
      await Promise.resolve();
    });
    expect(mockPatchSalesPipeline).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ sales_note: "Updated sales note" }),
    );
  });

  it("calls patchSalesPipeline when saving next follow-up date", async () => {
    await renderPage();
    const dateInput = container.querySelector('input[type="date"]') as HTMLInputElement;
    await act(async () => {
      setFieldValue(dateInput, "2026-07-15");
    });
    const saveButton = Array.from(container.querySelectorAll("button")).find((btn) =>
      btn.textContent?.includes("Save"),
    );
    await act(async () => {
      saveButton!.click();
      await Promise.resolve();
    });
    expect(mockPatchSalesPipeline).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ next_follow_up_at: "2026-07-15T09:00:00Z" }),
    );
  });

  it("calls patchSalesPipeline when saving assignee details", async () => {
    await renderPage();
    const nameInput = container.querySelector('[data-testid="assignee-name-1"]') as HTMLInputElement;
    const emailInput = container.querySelector('[data-testid="assignee-email-1"]') as HTMLInputElement;
    await act(async () => {
      setFieldValue(nameInput, "Bob Sales");
      setFieldValue(emailInput, "bob@example.com");
    });
    const saveButton = Array.from(container.querySelectorAll("button")).find((btn) =>
      btn.textContent?.includes("Save"),
    );
    await act(async () => {
      saveButton!.click();
      await Promise.resolve();
    });
    expect(mockPatchSalesPipeline).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        assigned_sales_name: "Bob Sales",
        assigned_sales_email: "bob@example.com",
      }),
    );
  });

  it("renders aging section", async () => {
    await renderPage();
    expect(container.querySelector('[data-testid="aging-section"]')).not.toBeNull();
    expect(container.textContent).toContain("8–14 days");
  });

  it("renders follow-up reminder sections", async () => {
    await renderPage();
    const section = container.querySelector('[data-testid="follow-up-reminders-section"]');
    expect(section).not.toBeNull();
    expect(section?.textContent).toContain("Q-100");
    expect(section?.textContent).toContain("Q-200");
  });

  it("renders salesperson performance table", async () => {
    await renderPage();
    const section = container.querySelector('[data-testid="salesperson-performance-section"]');
    expect(section).not.toBeNull();
    expect(section?.textContent).toContain("Alice");
    expect(section?.textContent).toContain("£4,000");
  });

  it("renders accepted vs rejected trend", async () => {
    await renderPage();
    const section = container.querySelector('[data-testid="accepted-rejected-trend-section"]');
    expect(section).not.toBeNull();
    expect(section?.textContent).toContain("2026-06");
    expect(section?.textContent).toContain("2");
    expect(section?.textContent).toContain("1");
  });

  it("renders monthly pipeline value table", async () => {
    await renderPage();
    const section = container.querySelector('[data-testid="monthly-pipeline-value-section"]');
    expect(section).not.toBeNull();
    expect(section?.textContent).toContain("2026-06");
    expect(section?.textContent).toContain("4,000");
  });
});
