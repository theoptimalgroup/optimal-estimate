import { describe, expect, it } from "vitest";

import {
  defaultMaterialSuppliers,
  defaultWorkBlockValues,
  formatSupplierDisplayName,
  migrateLegacyMaterialRows,
  workBlockToSnapshot,
} from "@/lib/eworks-calculate-schema";

describe("material supplier names", () => {
  it("defaults supplier card label to Supplier 1", () => {
    const suppliers = defaultMaterialSuppliers();
    expect(formatSupplierDisplayName(suppliers[0], 0)).toBe("Supplier 1");
    expect(suppliers[0].supplier_name).toBe("");
  });

  it("uses entered supplier name for display label", () => {
    expect(
      formatSupplierDisplayName({ supplier_name: "Travis Perkins" }, 0),
    ).toBe("Travis Perkins");
  });

  it("falls back when supplier name is cleared", () => {
    expect(formatSupplierDisplayName({ supplier_name: "   " }, 1)).toBe("Supplier 2");
  });

  it("persists supplier_name through snapshot round-trip", () => {
    const work = defaultWorkBlockValues("Electrician");
    work.materials_to_order = [
      {
        supplier_name: "Travis Perkins",
        delivery_charge: 5,
        links: [{ link: "Cable", quantity: 2, cost: 10 }],
      },
    ];
    const normalized = workBlockToSnapshot(work);
    expect(normalized.materials_to_order?.[0]?.supplier_name).toBe("Travis Perkins");
  });

  it("handles legacy sessions without supplier_name", () => {
    const migrated = migrateLegacyMaterialRows([
      { link: "Bolt", quantity: 2, cost: 20 },
    ]);
    expect(migrated[0].supplier_name).toBe("");
    expect(formatSupplierDisplayName(migrated[0], 0)).toBe("Supplier 1");
  });

  it("preserves supplier names when multiple suppliers exist", () => {
    const work = defaultWorkBlockValues("Electrician");
    work.materials_to_order = [
      {
        supplier_name: "Travis Perkins",
        delivery_charge: 0,
        links: [{ link: "A", quantity: 1, cost: 1 }],
      },
      {
        supplier_name: "",
        delivery_charge: 0,
        links: [{ link: "B", quantity: 1, cost: 2 }],
      },
    ];
    const snapshot = workBlockToSnapshot(work);
    expect(snapshot.materials_to_order?.[0]?.supplier_name).toBe("Travis Perkins");
    expect(snapshot.materials_to_order?.[1]?.supplier_name).toBe("");
    expect(formatSupplierDisplayName(snapshot.materials_to_order![1], 1)).toBe("Supplier 2");
  });
});
