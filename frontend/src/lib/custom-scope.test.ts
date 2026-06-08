import { describe, expect, it } from "vitest";

import { defaultWorkBlockValues } from "@/lib/eworks-calculate-schema";
import {
  isWorkBlockProductComplete,
  shouldConfirmSwitchToCustom,
  shouldConfirmSwitchToProduct,
} from "@/lib/custom-scope";
import { formatWorkCardTitle, formatWorkLabel } from "@/lib/work-label";

describe("custom scope helpers", () => {
  it("detects when switching to custom scope should confirm", () => {
    const work = defaultWorkBlockValues("Carpenter");
    expect(shouldConfirmSwitchToCustom(work)).toBe(false);

    expect(
      shouldConfirmSwitchToCustom({
        ...work,
        selected_product_id: 5,
        product_name: "Painting",
      }),
    ).toBe(true);
  });

  it("detects when switching to product should confirm", () => {
    const work = defaultWorkBlockValues("Carpenter");
    expect(shouldConfirmSwitchToProduct(work)).toBe(false);

    expect(
      shouldConfirmSwitchToProduct({
        ...work,
        is_custom_scope: true,
        custom_title: "Custom item",
        scope: "Do bespoke work",
      }),
    ).toBe(true);
  });

  it("validates product completion for catalog or custom scope", () => {
    const work = defaultWorkBlockValues("Carpenter");
    expect(isWorkBlockProductComplete(work)).toBe(false);
    expect(isWorkBlockProductComplete({ ...work, selected_product_id: 3 })).toBe(true);
    expect(
      isWorkBlockProductComplete({
        ...work,
        is_custom_scope: true,
        custom_title: "Custom",
        scope: "Scope text",
      }),
    ).toBe(true);
  });
});

describe("custom scope labels", () => {
  it("uses custom title in card and review labels", () => {
    const work = {
      is_custom_scope: true,
      custom_title: "One-off repair",
      scope: "Repair damaged cladding",
    };
    expect(formatWorkCardTitle(work)).toBe("One-off repair");
    expect(formatWorkLabel(work)).toBe("One-off repair");
  });
});
