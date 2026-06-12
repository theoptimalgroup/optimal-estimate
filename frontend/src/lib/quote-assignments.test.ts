import { describe, expect, it } from "vitest";

import { formatAppointmentWindow, formatAssignedAt } from "@/lib/quote-assignments";

describe("formatAppointmentWindow", () => {
  it("omits repeated date for same-day appointments", () => {
    const formatted = formatAppointmentWindow(
      "2026-06-15T08:00:00Z",
      "2026-06-15T09:30:00Z",
    );
    expect(formatted).toBe("15 Jun 2026, 08:00 – 09:30");
    expect(formatted).not.toContain("15 Jun 2026, 08:00 – 15 Jun 2026");
  });

  it("shows both dates when appointment spans days", () => {
    expect(
      formatAppointmentWindow("2026-06-15T08:00:00Z", "2026-06-16T09:30:00Z"),
    ).toBe("15 Jun 2026, 08:00 – 16 Jun 2026, 09:30");
  });

  it("shows start only when end is missing", () => {
    expect(formatAppointmentWindow("2026-06-15T08:00:00Z", null)).toBe(
      formatAssignedAt("2026-06-15T08:00:00Z"),
    );
  });

  it("returns Not available when start and end are missing", () => {
    expect(formatAppointmentWindow(null, null)).toBe("Not available");
    expect(formatAppointmentWindow(undefined, undefined)).toBe("Not available");
  });
});
