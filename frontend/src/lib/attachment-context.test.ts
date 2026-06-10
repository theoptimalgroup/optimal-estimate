import { describe, expect, it } from "vitest";

import {
  attachmentMediaContext,
  formatAttachmentContextLabel,
  formatAttachmentProductLine,
  formatAttachmentScopeLine,
} from "@/lib/attachment-context";
import type { AttachmentMeta, WorkBlockFormValues } from "@/lib/eworks-calculate-schema";

const emptyWorkValues = {} as WorkBlockFormValues;

function attachment(overrides: Partial<AttachmentMeta> = {}): AttachmentMeta {
  return {
    id: "att-1",
    file_name: "photo.jpg",
    size: 1024,
    media_type: "photo",
    stored_name: "stored.jpg",
    ...overrides,
  };
}

describe("formatAttachmentContextLabel", () => {
  it("trims, collapses whitespace, and strips HTML", () => {
    expect(formatAttachmentContextLabel("  <strong>Plant</strong>   Room  ")).toBe("Plant Room");
    expect(formatAttachmentContextLabel("line one\nline two")).toBe("line one line two");
  });

  it("truncates long text with ellipsis", () => {
    const long = "A".repeat(150);
    expect(formatAttachmentContextLabel(long, 100)).toBe(`${"A".repeat(100)}…`);
  });

  it("returns Not available for empty input", () => {
    expect(formatAttachmentContextLabel("")).toBe("Not available");
    expect(formatAttachmentContextLabel(null)).toBe("Not available");
  });
});

describe("formatAttachmentProductLine", () => {
  it("shows product name when available", () => {
    const file = attachment({ product_name: "74 MOANOR ROAD", is_custom_scope: false });
    expect(formatAttachmentProductLine(file, emptyWorkValues)).toBe("Product: 74 MOANOR ROAD");
  });

  it("shows custom scope title for custom work", () => {
    const file = attachment({
      is_custom_scope: true,
      custom_scope_title: "Bespoke cladding repair",
      product_name: "Bespoke cladding repair",
    });
    expect(formatAttachmentProductLine(file, emptyWorkValues)).toBe("Custom: Bespoke cladding repair");
  });

  it("falls back to work block label when product name missing", () => {
    const file = attachment({ work_block_label: "Work 1", is_custom_scope: false });
    expect(formatAttachmentProductLine(file, emptyWorkValues)).toBe("Work: Work 1");
  });
});

describe("formatAttachmentScopeLine", () => {
  const fullScope = "A".repeat(200);

  it("does not render full scope_snapshot without truncation", () => {
    const file = attachment({ scope_snapshot: fullScope, product_name: "Plant Room" });
    const line = formatAttachmentScopeLine(file);
    expect(line).not.toBe(`Scope: ${fullScope}`);
    expect(line).toBe(`Scope: ${"A".repeat(100)}…`);
  });

  it("shows short scope label from snapshot when no title labels", () => {
    const file = attachment({ scope_snapshot: "scope", product_name: "74 MOANOR ROAD" });
    expect(formatAttachmentScopeLine(file)).toBe("Scope: scope");
  });

  it("prefers custom_scope_title over snapshot", () => {
    const file = attachment({
      is_custom_scope: true,
      custom_scope_title: "Roof hatch",
      scope_snapshot: "Long scope description that should not appear in context.",
      product_name: "Roof hatch",
    });
    expect(formatAttachmentScopeLine(file)).toBe("Scope: Roof hatch");
    expect(formatAttachmentScopeLine(file)).not.toContain("Long scope description");
  });

  it("does not fall back to live form scope values", () => {
    const file = attachment({ product_name: "Plant Room" });
    expect(formatAttachmentScopeLine(file)).toBeNull();
  });
});

describe("attachmentMediaContext", () => {
  it("keeps product and scope lines compact for long descriptions", () => {
    const longScope = "Repair ".repeat(40);
    const file = attachment({
      product_name: "Plant Room",
      scope_snapshot: longScope,
    });
    const context = attachmentMediaContext(file, emptyWorkValues);
    expect(context.productLine).toBe("Product: Plant Room");
    expect(context.scopeLine?.length).toBeLessThan(120);
    expect(context.scopeLine).not.toContain(longScope);
  });
});
