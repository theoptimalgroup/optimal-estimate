import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("@/lib/quote-assignments", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/quote-assignments")>();
  return {
    ...original,
    startAssignmentEstimate: vi.fn(),
  };
});

import { EngineerAssignmentCard } from "@/components/engineer/engineer-assignment-card";
import type { QuoteAssignment } from "@/lib/quote-assignments";

function longScope() {
  return Array.from({ length: 40 }, (_, index) => `Scope line ${index + 1} with details.`).join("\n\n");
}

function baseAssignment(overrides: Partial<QuoteAssignment> = {}): QuoteAssignment {
  return {
    id: 3,
    synced_quote_id: 10,
    eworks_quote_id: 100,
    quote_ref: "Q-100",
    assigned_user_id: "user-1",
    assigned_user_email: "engineer@example.com",
    assigned_user_name: "Alex Engineer",
    assignment_type: "engineer",
    assignee_kind: "registered",
    status: "assigned",
    assignment_token_created_at: null,
    assignment_token_expires_at: null,
    assignment_token_revoked_at: null,
    assigned_by_user_id: "mgr-1",
    assigned_by_email: "manager@example.com",
    assigned_at: "2026-06-05T09:00:00Z",
    notes: null,
    assignment_link: null,
    quote_summary: {
      synced_quote_id: 10,
      eworks_quote_id: 100,
      quote_ref: "Q-100",
      customer_name: "Acme Ltd",
      site_address: "1 High Street",
      quote_date: null,
      expiry_date: null,
      description: longScope(),
      tags: [],
    },
    can_start_estimate: true,
    ...overrides,
  };
}

describe("EngineerAssignmentCard", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    mockPush.mockReset();
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

  async function renderCard(assignment: QuoteAssignment) {
    await act(async () => {
      root.render(
        <EngineerAssignmentCard assignment={assignment} variant="active" testIdPrefix="engineer-assignment" />,
      );
      await Promise.resolve();
    });
  }

  it("renders compact scope preview with line clamp classes", async () => {
    await renderCard(baseAssignment());
    const preview = container.querySelector('[data-testid="engineer-assignment-description-3-text"]');
    expect(preview?.className).toContain("line-clamp-3");
    expect(preview?.className).toContain("overflow-hidden");
    expect(preview?.textContent).toContain("Scope line 1");
    expect(preview?.textContent).not.toContain("\n\n");
  });

  it("shows view details toggle for long scope text", async () => {
    await renderCard(baseAssignment());
    expect(container.querySelector('[data-testid="engineer-assignment-description-3-toggle"]')).toBeTruthy();
  });

  it("shows quote ref, customer, appointment, and assigned by", async () => {
    await renderCard(
      baseAssignment({
        appointment_start_at: "2026-06-15T08:00:00Z",
        appointment_end_at: "2026-06-15T09:30:00Z",
        has_calculation_session: true,
        quote_summary: {
          ...baseAssignment().quote_summary!,
          description: "Short scope note.",
        },
      }),
    );
    expect(container.textContent).toContain("Q-100");
    expect(container.textContent).toContain("Acme Ltd");
    expect(container.textContent).toContain("Appointment:");
    expect(container.textContent).toContain("15 Jun 2026, 08:00 – 09:30");
    expect(container.textContent).not.toContain("15 Jun 2026, 08:00 – 15 Jun 2026");
    expect(container.textContent).toContain("Engineer:");
    expect(container.textContent).toContain("Alex Engineer");
    expect(container.textContent).toContain("Assigned by:");
    expect(container.textContent).toContain("Continue your estimate");
  });
});
