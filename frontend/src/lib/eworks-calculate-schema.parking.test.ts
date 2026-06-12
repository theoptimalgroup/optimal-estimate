import { describe, expect, it } from "vitest";
import {
  calculateCcTotal,
  calculateParkingCharge,
  calculateQuoteParkingTotal,
  defaultQuoteCharges,
  defaultWorkBlockValues,
  worksCombinedDuration,
} from "@/lib/eworks-calculate-schema";

describe("parking duration calculations", () => {
  it("treats one day as eight hours", () => {
    const works = [
      {
        ...defaultWorkBlockValues("Electrician"),
        engineers_required: true,
        engineers_needed: 1,
        engineer_time_unit: "days" as const,
        engineer_time_value: 1,
      },
      {
        ...defaultWorkBlockValues("Electrician"),
        engineers_required: true,
        engineers_needed: 1,
        engineer_time_unit: "hours" as const,
        engineer_time_value: 2,
      },
    ];
    expect(worksCombinedDuration(works)).toEqual({ days: 1, hours: 2, totalHours: 10 });
  });

  it("calculates per hour parking from combined duration", () => {
    const charge = calculateParkingCharge("hourly", {
      ratePerDay: 0,
      ratePerHour: 10,
      days: 1,
      hours: 2,
      vehicles: 1,
    });
    expect(charge).toBe(100);
  });

  it("calculates per day parking pro-rata for partial days", () => {
    const charge = calculateParkingCharge("fixed", {
      ratePerDay: 126,
      ratePerHour: 0,
      days: 0,
      hours: 4,
      vehicles: 1,
    });
    expect(charge).toBe(63);
  });

  it("updates quote parking total from work durations", () => {
    const works = [
      {
        ...defaultWorkBlockValues("Electrician"),
        engineers_required: true,
        engineers_needed: 1,
        engineer_time_unit: "hours" as const,
        engineer_time_value: 4,
      },
    ];
    const total = calculateQuoteParkingTotal(
      {
        ...defaultQuoteCharges(),
        parking_required: true,
        parking_type: "fixed",
        parking_fixed_amount: 126,
      },
      works,
    );
    expect(total).toBe(63);
  });

  it("updates quote CC total using whole chargeable days", () => {
    const works = [
      {
        ...defaultWorkBlockValues("Electrician"),
        engineers_required: true,
        engineers_needed: 1,
        engineer_time_unit: "hours" as const,
        engineer_time_value: 4.5,
      },
    ];
    const total = calculateCcTotal(
      {
        ...defaultQuoteCharges(),
        congestion_required: true,
        congestion_amount: 28.8,
      },
      works,
    );
    expect(total).toBe(28.8);
  });

  it("charges one CC day for eight hours", () => {
    const works = [
      {
        ...defaultWorkBlockValues("Electrician"),
        engineers_required: true,
        engineers_needed: 1,
        engineer_time_unit: "hours" as const,
        engineer_time_value: 8,
      },
    ];
    const total = calculateCcTotal(
      {
        ...defaultQuoteCharges(),
        congestion_required: true,
        congestion_amount: 18,
      },
      works,
    );
    expect(total).toBe(18);
  });
});
