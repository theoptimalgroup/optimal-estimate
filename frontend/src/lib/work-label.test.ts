import { describe, expect, it } from "vitest";

import {
  defaultOpenWorkIndexes,
  formatProductLabel,
  formatQuoteSummaryTitle,
  formatWorkLabel,
  isScopeLong,
} from "@/lib/work-label";

describe("formatQuoteSummaryTitle", () => {
  it("returns neutral submission title", () => {
    expect(formatQuoteSummaryTitle()).toBe("Submission Summary");
  });
});

describe("defaultOpenWorkIndexes", () => {
  it("opens a single work with short scope by default", () => {
    expect(
      defaultOpenWorkIndexes([
        {
          work_index: 0,
          scope: "Repaint hallway",
        },
      ]),
    ).toEqual([0]);
  });

  it("keeps a single work collapsed when scope is long", () => {
    expect(
      defaultOpenWorkIndexes([
        {
          work_index: 2,
          scope: "A".repeat(80),
        },
      ]),
    ).toEqual([]);
  });

  it("keeps multiple works collapsed by default", () => {
    expect(
      defaultOpenWorkIndexes([
        { work_index: 0, scope: "Short scope" },
        { work_index: 1, scope: "Another scope" },
      ]),
    ).toEqual([]);
  });
});

describe("isScopeLong", () => {
  it("detects scopes longer than the preview threshold", () => {
    expect(isScopeLong("Short scope")).toBe(false);
    expect(isScopeLong("A".repeat(80))).toBe(true);
  });
});

describe("formatWorkLabel", () => {
  it("uses product label instead of work number", () => {
    expect(
      formatWorkLabel({
        product_name: "Decoration - 2 Bedroom Flat",
        product_code: "D--0001",
      }),
    ).toBe("Decoration - 2 Bedroom Flat · D--0001");
  });
});

describe("formatProductLabel", () => {
  it("formats name and code with separator", () => {
    expect(formatProductLabel("Decoration - 2 Bedroom Flat", "D--0001")).toBe(
      "Decoration - 2 Bedroom Flat · D--0001",
    );
  });
});
