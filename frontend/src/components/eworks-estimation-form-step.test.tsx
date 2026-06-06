import React from "react";
import { describe, expect, it } from "vitest";
import { JSDOM } from "jsdom";
import { renderToStaticMarkup } from "react-dom/server";
import { useForm } from "react-hook-form";

import { EworksEstimationFormStep } from "@/components/eworks-estimation-form-step";
import { defaultQuestionnaireValues, type QuestionnaireFormValues } from "@/lib/eworks-calculate-schema";
import type { FromLinkResponse } from "@/lib/eworks-session";

const baseStep1: FromLinkResponse["step1"] = {
  quote_number: "Q-1001",
  job_number: "J-2001",
  client_name: "Lamberts Chartered Surveyors",
  trade_name: "Carpenter",
  property_address: "1 Nile Street",
  engineer_name: "Alex Engineer",
  property_manager_name: "Kira Mcintyre",
  contact: "Alex - 07960696064",
  date_visited: "2026-05-22",
  quote_description: "<strong>Access</strong><br />Quote for window replacement",
  findings_report: "",
  congestion_required: false,
  congestion_amount: 0,
  travel: 0,
};

const baseResolved: FromLinkResponse["resolved"] = {
  client_id: "11111111-1111-1111-1111-111111111111",
  trade_id: "22222222-2222-2222-2222-222222222222",
  rule_version: "",
  formula_source: "none",
  client_fee_pct: 0,
};

function renderStep(
  step1: FromLinkResponse["step1"] = baseStep1,
  resolved: FromLinkResponse["resolved"] = baseResolved,
  chargeOverrides: Partial<QuestionnaireFormValues> = {},
) {
  function StepHarness() {
    const form = useForm<QuestionnaireFormValues>({
      defaultValues: { ...defaultQuestionnaireValues, ...chargeOverrides },
    });
    return (
      <EworksEstimationFormStep
        step1={step1}
        resolved={resolved}
        control={form.control}
        register={form.register}
        watch={form.watch}
        setValue={form.setValue}
        errors={form.formState.errors}
      />
    );
  }

  const markup = renderToStaticMarkup(<StepHarness />);
  return new JSDOM(markup).window.document;
}

describe("EworksEstimationFormStep", () => {
  it("renders organized step 1 sections", () => {
    const doc = renderStep();

    expect(doc.querySelector('[data-testid="estimation-quote-summary"]')).not.toBeNull();
    expect(doc.querySelector('[data-testid="estimation-job-information"]')).not.toBeNull();
    expect(doc.querySelector('[data-testid="estimation-property-client"]')).not.toBeNull();
    expect(doc.querySelector('[data-testid="estimation-quote-description"]')).not.toBeNull();
    expect(doc.querySelector('[data-testid="estimation-findings-report"]')).not.toBeNull();
    expect(doc.querySelector('[data-testid="findings-report-input"]')).not.toBeNull();
    expect(doc.querySelector('[data-testid="additional-charges-section"]')).not.toBeNull();
  });

  it("shows customer not matched badge for unknown customer", () => {
    const doc = renderStep({ ...baseStep1, client_name: "Unknown Customer" });

    const badge = doc.querySelector('[data-testid="customer-not-matched-badge"]');
    expect(badge?.textContent).toContain("Customer not matched");
  });

  it("renders sanitized quote description without raw html tags in text content", () => {
    const doc = renderStep();
    const richText = doc.querySelector('[data-testid="quote-description-rich-text"]');
    const text = richText?.textContent ?? "";

    expect(text).toContain("Access");
    expect(text).toContain("Quote for window replacement");
    expect(text).not.toContain("<span");
    expect(text).not.toContain("<br");
  });

  it("renders additional charges after findings report", () => {
    const doc = renderStep();
    const sections = Array.from(doc.querySelectorAll("section[data-testid]")).map(
      (node) => node.getAttribute("data-testid"),
    );
    const findingsIndex = sections.indexOf("estimation-findings-report");
    const chargesIndex = sections.indexOf("additional-charges-section");
    expect(findingsIndex).toBeGreaterThanOrEqual(0);
    expect(chargesIndex).toBeGreaterThan(findingsIndex);
  });

  it("does not show quote-level charge helper text", () => {
    const doc = renderStep();
    expect(doc.body.textContent).not.toContain("Applied once to the whole quote, not per work item.");
  });

  it("keeps findings report editable", () => {
    const doc = renderStep();
    const findingsInput = doc.querySelector('[data-testid="findings-report-input"]');

    expect(findingsInput?.tagName.toLowerCase()).toBe("textarea");
    expect(findingsInput?.getAttribute("disabled")).toBeNull();
  });

  it("does not show rate rule or commission details", () => {
    const doc = renderStep(baseStep1, {
      ...baseResolved,
      formula_source: "manual",
      client_fee_pct: 15,
      xlsx_client_name: "Manual Estimate",
    });
    const text = doc.body.textContent ?? "";

    expect(text).not.toContain("Rate rule");
    expect(text).not.toContain("COMMISSION");
    expect(text).not.toContain("Manual Estimate");
    expect(text).not.toContain("Rule:");
  });

  it("shows parking and congestion charges but hides ULEZ and waste disposal", () => {
    const doc = renderStep(baseStep1, baseResolved, {
      ulez_required: true,
      ulez_amount: 12.5,
      waste_disposal_required: true,
      waste_disposal_amount: 45,
    });
    const text = doc.body.textContent ?? "";

    expect(text).toContain("Parking charge");
    expect(text).toContain("Congestion charge");
    expect(text).toContain("Travel charge");
    expect(text).toContain("Other charge");
    expect(text).not.toContain("ULEZ charge");
    expect(text).not.toContain("Waste disposal charge");
  });

  it("shows quote-level parking vehicle count and GPS snapshot fields", () => {
    const doc = renderStep(baseStep1, baseResolved, {
      parking_required: true,
      parking_type: "hourly",
      parking_rate_per_hour: 10,
      parking_hours: 2,
      parking_vehicles: 2,
    });

    expect(doc.querySelector('[data-testid="quote-parking-vehicles"]')).not.toBeNull();
    expect(doc.querySelector('[data-testid="quote-parking-gps"]')).not.toBeNull();
    expect(doc.body.textContent).toContain("Number of vehicles");
    expect(doc.body.textContent).toContain("GPS snapshot");
    expect(doc.querySelector('[data-testid="quote-parking-notes"]')).not.toBeNull();
  });
});
