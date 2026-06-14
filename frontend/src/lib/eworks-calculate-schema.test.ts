import { describe, expect, it } from "vitest";

import {
  coerceQuestionnaireValues,
  defaultMaterialSuppliers,
  defaultQuestionnaireValues,
  defaultWorkBlockValues,
  formatCurrency,
  formatSupplierDisplayName,
  grandTotalMaterials,
  mergeQuestionnaireWithSessionStep2,
  migrateLegacyMaterialRows,
  normalizeSharedWorkBlocks,
  questionnaireSchema,
  questionnaireToStep2,
  shelfMaterialLineTotal,
  shelfMaterialsCostTotal,
  shelfMaterialsTotal,
  step2ToQuestionnaire,
  supplierMaterialsSubtotal,
  supplierMaterialsTotal,
  workBlockHasProductContext,
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

describe("shared work block product context", () => {
  it("accepts product_name without selected_product_id", () => {
    expect(
      workBlockHasProductContext({
        selected_product_id: null,
        product_name: "Dishwasher",
      }),
    ).toBe(true);
  });

  it("maps shared snapshot without engineer_time_unit into questionnaire values", () => {
    const questionnaire = step2ToQuestionnaire(
      {
        works: [
          {
            scope: "Shared product scope",
            selected_product_id: 42,
            product_name: "Dishwasher",
            product_code: "DW-001",
            time_frame: "1.5 hours",
            engineers_required: true,
            engineers_needed: 1,
          },
        ],
      },
      "Carpenter",
    );

    expect(questionnaire.works[0].selected_product_id).toBe(42);
    expect(questionnaire.works[0].product_name).toBe("Dishwasher");
    expect(questionnaire.works[0].scope).toBe("Shared product scope");
  });

  it("merges shared product context into local draft before submit", () => {
    const local = defaultWorkBlockValues("Carpenter");
    local.scope = "";
    local.selected_product_id = null;
    local.product_name = "";

    const merged = mergeQuestionnaireWithSessionStep2(
      { ...defaultQuestionnaireValues, works: [local] },
      {
        works: [
          {
            scope: "Shared product scope",
            selected_product_id: 42,
            product_name: "Dishwasher",
            product_code: "DW-001",
            time_frame: "1.5 hours",
            engineers_required: true,
            engineers_needed: 1,
          },
        ],
      },
      "Carpenter",
    );

    expect(merged.works[0].selected_product_id).toBe(42);
    expect(merged.works[0].product_name).toBe("Dishwasher");
    expect(merged.works[0].scope).toBe("Shared product scope");
  });

  it("normalizes shared scope-only work block to custom scope", () => {
    const normalized = normalizeSharedWorkBlocks({
      works: [
        {
          scope: "Repair leaking roof hatch and replace flashing",
          engineers_required: true,
          engineers_needed: 1,
          engineer_time_value: 1.5,
        },
      ],
    });

    expect(normalized.works?.[0]?.is_custom_scope).toBe(true);
    expect(normalized.works?.[0]?.custom_title).toBe("Repair leaking roof hatch and replace flashing");
    expect(workBlockHasProductContext(normalized.works![0])).toBe(true);
  });

  it("maps shared scope-only snapshot into questionnaire custom scope display", () => {
    const questionnaire = step2ToQuestionnaire(
      {
        works: [
          {
            scope: "Shared quote description scope",
            engineers_required: true,
            engineers_needed: 1,
            engineer_time_value: 1.5,
          },
        ],
      },
      "Carpenter",
    );

    expect(questionnaire.works[0].is_custom_scope).toBe(true);
    expect(questionnaire.works[0].custom_title).toBe("Shared quote description scope");
    expect(questionnaire.works[0].product_name).toBe("Shared quote description scope");
  });

  it("merges shared scope-only context before submit validation", () => {
    const local = defaultWorkBlockValues("Carpenter");
    local.scope = "";
    local.selected_product_id = null;
    local.product_name = "";

    const merged = mergeQuestionnaireWithSessionStep2(
      { ...defaultQuestionnaireValues, works: [local] },
      {
        works: [
          {
            scope: "Shared scope from quote description",
            engineers_required: true,
            engineers_needed: 1,
            engineer_time_value: 1.5,
          },
        ],
      },
      "Carpenter",
    );

    expect(merged.works[0].is_custom_scope).toBe(true);
    expect(merged.works[0].custom_title).toBe("Shared scope from quote description");
    expect(merged.works[0].scope).toBe("Shared scope from quote description");
  });

  it("does not overwrite real shared product during normalization", () => {
    const normalized = normalizeSharedWorkBlocks({
      works: [
        {
          scope: "Shared product scope",
          selected_product_id: 42,
          product_name: "Dishwasher",
          engineers_required: true,
          engineers_needed: 1,
        },
      ],
    });

    expect(normalized.works?.[0]?.is_custom_scope).toBeFalsy();
    expect(normalized.works?.[0]?.selected_product_id).toBe(42);
    expect(normalized.works?.[0]?.product_name).toBe("Dishwasher");
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

  it("calculates off-shelf line total as quantity times cost per item", () => {
    expect(shelfMaterialLineTotal({ quantity: 10, cost: 10 })).toBe(100);
  });

  it("stores section total in shelfMaterialsCostTotal for snapshots", () => {
    const rows = [{ link: "1sdvas", quantity: 10, cost: 10 }];
    expect(shelfMaterialsCostTotal(rows)).toBe(100);
  });

  it("supplier materials-to-order calculation still uses quantity times cost per item", () => {
    expect(
      supplierMaterialsTotal({
        supplier_name: "A",
        delivery_charge: 5,
        links: [{ link: "Item", quantity: 2, cost: 60 }],
      }),
    ).toBe(125);
  });

  it("snapshot includes off-shelf line_total and section_total", () => {
    const work = defaultWorkBlockValues("Electrician");
    work.shelf_materials_rows = [{ link: "1sdvas", quantity: 10, cost: 10 }];
    const snapshot = workBlockToSnapshot(work);
    expect(snapshot.shelf_materials_rows?.[0]?.line_total).toBe(100);
    expect(Number(snapshot.shelf_materials_cost)).toBe(100);
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

describe("subcontractor labour", () => {
  it("maps subcontractor work block to step2 snapshot with backend fields", () => {
    const work = {
      ...defaultWorkBlockValues("Scaffolder"),
      labour_entry_type: "subcontractor" as const,
      subcontractor_name: "Danny Arnold Scaffolding",
      subcontractor_labour_cost: 1500,
      subcontractor_units_type: "Days" as const,
      engineers_needed: 3,
      engineer_time_value: 6,
      skill_required: "Scaffolder",
    };
    const snapshot = workBlockToSnapshot(work);

    expect(snapshot.labour_type).toBe("subcontractor");
    expect(snapshot.subcontractor_name).toBe("Danny Arnold Scaffolding");
    expect(snapshot.subcontractor_labour_cost).toBe(1500);
    expect(snapshot.subcontractor_units_type).toBe("Days");
    expect(snapshot.engineers).toBe(3);
    expect(snapshot.days).toBe(6);
    expect(snapshot.hours).toBe(0);
    expect(snapshot.subcontractors).toBe("Danny Arnold Scaffolding");
  });

  it("restores subcontractor fields from snapshot", () => {
    const questionnaire = step2ToQuestionnaire(
      {
        works: [
          {
            scope: "Scaffold access",
            skill_required: "Scaffolder",
            labour_type: "subcontractor",
            subcontractor_name: "Danny Arnold Scaffolding",
            subcontractor_labour_cost: 1500,
            subcontractor_units_type: "Days",
            engineers_needed: 3,
            days: 6,
            hours: 0,
          },
        ],
      },
      "Scaffolder",
    );

    expect(questionnaire.works[0].labour_entry_type).toBe("subcontractor");
    expect(questionnaire.works[0].subcontractor_name).toBe("Danny Arnold Scaffolding");
    expect(questionnaire.works[0].subcontractor_labour_cost).toBe(1500);
    expect(questionnaire.works[0].subcontractor_units_type).toBe("Days");
    expect(questionnaire.works[0].engineers_needed).toBe(3);
    expect(questionnaire.works[0].engineer_time_value).toBe(6);
  });

  it("rejects invalid subcontractor labour cost and duration", () => {
    const values = coerceQuestionnaireValues({
      ...defaultQuestionnaireValues,
      works: [
        {
          ...defaultWorkBlockValues("Scaffolder"),
          labour_entry_type: "subcontractor",
          subcontractor_name: "Example Subby",
          subcontractor_labour_cost: 0,
          subcontractor_units_type: "Days",
          engineers_needed: 1,
          engineer_time_value: 0,
        },
      ],
    });
    const parsed = questionnaireSchema.safeParse(values);
    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      const messages = parsed.error.issues.map((issue) => issue.message);
      expect(messages).toContain("Subcontractor labour cost must be greater than 0");
      expect(messages).toContain("Duration must be greater than 0");
    }
  });
});
