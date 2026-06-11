import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CallBackDashboard } from "@/lib/call-back-dashboard";

const mockGetCallBackDashboard = vi.fn();
const mockPatchCallBackTracking = vi.fn();

vi.mock("@/lib/call-back-dashboard", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/call-back-dashboard")>();
  return {
    ...original,
    getCallBackDashboard: (...args: Parameters<typeof original.getCallBackDashboard>) =>
      mockGetCallBackDashboard(...args),
    patchCallBackTracking: (...args: Parameters<typeof original.patchCallBackTracking>) =>
      mockPatchCallBackTracking(...args),
  };
});

import { CallBackDashboardPage } from "@/components/call-back-dashboard/call-back-dashboard-page";

function baseQuote(
  overrides: Partial<CallBackDashboard["categories"]["overdue"]["quotes"][0]> = {},
) {
  return {
    id: 1,
    quote_ref: "Q-100",
    eworks_quote_id: 100,
    customer_name: "Acme Ltd",
    site_address: "1 High Street",
    quote_value: 1500,
    status: "5",
    status_name: "Call Back",
    tags: [],
    created_on: "2026-05-01",
    last_updated_on: "2026-06-01",
    days_since_updated: 10,
    assigned_name: null,
    assigned_email: null,
    call_note: null,
    last_called_at: null,
    next_call_at: null,
    call_status: "no_call_date" as const,
    quote_detail_link: "/manager/quotes?quote_id=1",
    ...overrides,
  };
}

function buildDashboard(): CallBackDashboard {
  const overdueQuote = baseQuote({
    id: 1,
    quote_ref: "Q-OVER",
    next_call_at: "2026-06-09T09:00:00Z",
    call_status: "overdue",
  });
  const todayQuote = baseQuote({
    id: 2,
    quote_ref: "Q-TODAY",
    next_call_at: "2026-06-11T09:00:00Z",
    call_status: "due_today",
  });
  const upcomingQuote = baseQuote({
    id: 3,
    quote_ref: "Q-UP",
    next_call_at: "2026-06-20T09:00:00Z",
    call_status: "upcoming",
  });
  const noDateQuote = baseQuote({ id: 4, quote_ref: "Q-NONE" });
  return {
    totals: {
      call_back_quotes: 4,
      total_quote_value: 6000,
      overdue_calls: 1,
      due_today_calls: 1,
      upcoming_calls: 1,
      no_call_date: 1,
      average_age_days: 8,
    },
    categories: {
      overdue: { count: 1, value: 1500, quotes: [overdueQuote] },
      due_today: { count: 1, value: 1500, quotes: [todayQuote] },
      upcoming: { count: 1, value: 1500, quotes: [upcomingQuote] },
      no_call_date: { count: 1, value: 1500, quotes: [noDateQuote] },
    },
  };
}

describe("CallBackDashboardPage", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    mockGetCallBackDashboard.mockReset();
    mockPatchCallBackTracking.mockReset();
    mockGetCallBackDashboard.mockResolvedValue(buildDashboard());
    mockPatchCallBackTracking.mockResolvedValue(undefined);

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

  async function renderPage(apiBase: "admin" | "manager" = "admin") {
    await act(async () => {
      root.render(<CallBackDashboardPage apiBase={apiBase} />);
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

  it("admin can open Call Back Dashboard", async () => {
    await renderPage("admin");
    expect(mockGetCallBackDashboard).toHaveBeenCalledWith("admin", undefined);
    expect(container.querySelector('[data-testid="call-back-dashboard-page"]')).toBeTruthy();
  });

  it("manager can open Call Back Dashboard", async () => {
    await renderPage("manager");
    expect(mockGetCallBackDashboard).toHaveBeenCalledWith("manager", undefined);
  });

  it("renders KPI cards", async () => {
    await renderPage();
    expect(container.querySelector('[data-testid="kpi-call-back-quotes"]')?.textContent).toContain("4");
    expect(container.querySelector('[data-testid="kpi-total-value"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="kpi-overdue"]')?.textContent).toContain("1");
  });

  it("renders call buckets", async () => {
    await renderPage();
    expect(container.querySelector('[data-testid="call-back-bucket-overdue"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="call-back-bucket-due_today"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="call-back-bucket-upcoming"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="call-back-bucket-no_call_date"]')).toBeTruthy();
  });

  it("displays quote ref customer and value", async () => {
    await renderPage();
    const card = container.querySelector('[data-testid="call-back-quote-1"]');
    expect(card?.textContent).toContain("Q-OVER");
    expect(card?.textContent).toContain("Acme Ltd");
  });

  it("user can set next call date and save", async () => {
    await renderPage();
    const dateInput = container.querySelector('[data-testid="next-call-4"]') as HTMLInputElement;
    setFieldValue(dateInput, "2026-06-25");
    const saveBtn = container.querySelector('[data-testid="call-back-quote-4"] button');
    await act(async () => {
      saveBtn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      await Promise.resolve();
    });
    expect(mockPatchCallBackTracking).toHaveBeenCalledWith(
      4,
      expect.objectContaining({ next_call_at: "2026-06-25T09:00:00Z" }),
    );
  });

  it("user can save call note", async () => {
    await renderPage();
    const textarea = container.querySelector('[data-testid="call-back-quote-4"] textarea') as HTMLTextAreaElement;
    setFieldValue(textarea, "Customer requested callback");
    const buttons = container.querySelectorAll('[data-testid="call-back-quote-4"] button');
    await act(async () => {
      buttons[0]?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      await Promise.resolve();
    });
    expect(mockPatchCallBackTracking).toHaveBeenCalledWith(
      4,
      expect.objectContaining({ call_note: "Customer requested callback" }),
    );
  });

  it("user can open quote link", async () => {
    await renderPage();
    const link = container.querySelector('[data-testid="call-back-quote-1"] a');
    expect(link?.getAttribute("href")).toBe("/manager/quotes?quote_id=1");
  });
});
