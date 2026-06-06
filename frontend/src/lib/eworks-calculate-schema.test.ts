import { describe, expect, it } from "vitest";

import {
  coerceQuestionnaireValues,
  defaultMaterialSuppliers,
  defaultQuestionnaireValues,
  defaultWorkBlockValues,
  formatCurrency,
  formatSupplierDisplayName,
  grandTotalMaterials,
  migrateLegacyMaterialRows,
  questionnaireToStep2,
  shelfMaterialsTotal,
  supplierMaterialsSubtotal,
  supplierMaterialsTotal,
  workBlockToSnapshot,
} from "@/lib/eworks-calculate-schema";

describe("quote charges", () => {
  it("zeros ULEZ and waste disposal in step2 payload", () => {
    const values = coerceQuestionnaireValues({
      ...defaultQuestionnaireValues,
      ulez_required: true,
      ulez_amount: 12.5,
      waste_disposal_required: true,
      waste_disposal_amount: 45,
      congestion_required: true,
      congestion_amount: 18,
    });
    const step2 = questionnaireToStep2(values);

    expect(step2.ulez_required).toBe(false);
    expect(step2.ulez_amount).toBe(0);
    expect(step2.waste_disposal_required).toBe(false);
    expect(step2.waste_disposal_amount).toBe(0);
    expect(step2.congestion_required).toBe(true);
    expect(step2.congestion_amount).toBe(18);
  });
});

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

describe("materials subtotals", () => {
  it("calculates supplier total from links and delivery", () => {
    expect(
      supplierMaterialsTotal({
        supplier_name: "Travis Perkins",
        delivery_charge: 5,
        links: [
          { link: "Cable", quantity: 2, cost: 10 },
          { link: "Tape", quantity: 1, cost: 20 },
        ],
      }),
    ).toBe(45);
  });

  it("includes delivery charge when no link rows have cost", () => {
    expect(
      supplierMaterialsTotal({
        supplier_name: "",
        delivery_charge: 12,
        links: [{ link: "", quantity: 0, cost: 0 }],
      }),
    ).toBe(12);
  });

  it("sums supplier materials subtotal across suppliers", () => {
    const work = defaultWorkBlockValues("Electrician");
    work.materials_to_order = [
      {
        supplier_name: "A",
        delivery_charge: 0,
        links: [{ link: "Item", quantity: 2, cost: 60 }],
      },
      {
        supplier_name: "B",
        delivery_charge: 20,
        links: [{ link: "Item", quantity: 1, cost: 80 }],
      },
    ];
    expect(supplierMaterialsSubtotal(work.materials_to_order)).toBe(220);
  });

  it("calculates shelf materials subtotal", () => {
    expect(
      shelfMaterialsTotal([
        { link: "Screw", quantity: 10, cost: 2.5 },
        { link: "Plug", quantity: 1, cost: 20 },
      ]),
    ).toBe(45);
  });

  it("calculates grand total materials", () => {
    const work = defaultWorkBlockValues("Electrician");
    work.materials_to_order = [
      {
        supplier_name: "A",
        delivery_charge: 0,
        links: [{ link: "Item", quantity: 1, cost: 200 }],
      },
    ];
    work.shelf_materials_rows = [{ link: "Shelf item", quantity: 3, cost: 15 }];
    expect(grandTotalMaterials(work)).toBe(245);
    expect(formatCurrency(grandTotalMaterials(work))).toBe("£245.00");
  });
});
