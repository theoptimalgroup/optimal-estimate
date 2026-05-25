# Optimal Estimate Calculator — Calculation Logic Specification

**Document Version:** v1.0  
**Purpose:** Standalone formula specification for Cursor/developer implementation.  
**Scope:** Estimating calculator calculation logic only.  
**Important:** This file defines the calculation engine rules. The frontend must not be the source of truth for final totals.

---

## 1. Calculation Engine Principles

The calculation engine must be:

```text
Backend-driven
Rule-based
Client + trade aware
Explainable
Auditable
Testable
Versioned
Repeatable
```

Every calculation must return:

```text
Input values
Matched rate rule
Formula breakdown
Line-level totals
Subtotal
VAT
Final total
Approval requirement
Warnings
Calculation snapshot
```

---

## 2. Core Formula Summary

```text
Final Quote Total =
Labour Total
+ Material Sell Total
+ Parking Total
+ Congestion Total
+ ULEZ Total
+ Waste Disposal Total
+ Travel Charge
+ Other Charges
+ VAT
```

More formally:

```text
Subtotal =
Labour Total
+ Material Sell Total
+ Chargeable Extras Total

VAT Total =
VAT Applicable Amount × VAT Rate

Final Total =
Subtotal + VAT Total
```

---

## 3. Main Calculation Inputs

### 3.1 Job Inputs

```text
job_id
job_number
client_id
client_name
property_address
date_visited
travel_time_minutes
```

### 3.2 Trade Inputs

```text
trade_id
trade_name
skill_required
labour_type
number_of_engineers
number_of_labourers
hours_on_site
days_on_site
```

### 3.3 Material Inputs

```text
material_name
supplier_name
supplier_link
quantity
unit_cost
delivery_cost
markup_type
markup_value
client_visible
```

### 3.4 Charge Inputs

```text
parking_required
parking_type
parking_rate_per_hour
parking_hours
parking_fixed_amount
parking_markup_type
parking_markup_value

congestion_required
congestion_amount
congestion_chargeable_to_client

ulez_required
ulez_amount
ulez_chargeable_to_client

waste_disposal_required
waste_disposal_amount

travel_charge
other_charge
other_charge_reason
```

### 3.5 Rule Inputs

```text
client_id
trade_id
hourly_rate
half_day_rate
day_rate
labourer_hourly_rate
labourer_day_rate
minimum_hours
minimum_charge
material_markup_type
material_markup_value
vat_rate
approval_threshold
minimum_margin_percentage
rounding_rule
active_from
active_to
rule_version
```

---

## 4. Rate Rule Lookup Logic

### 4.1 Primary Rule Lookup

The calculation engine must find the active rule using:

```text
Client + Trade + Active Date
```

Formula:

```text
Matched Rule =
rate_rules where
client_id = selected_client_id
AND trade_id = selected_trade_id
AND is_active = true
AND active_from <= quote_date
AND (active_to is null OR active_to >= quote_date)
```

### 4.2 Rule Lookup Priority

If multiple rules exist, use this priority:

```text
1. Exact client + exact trade + active date
2. Exact client + default trade rule
3. Default client rule + exact trade
4. Global default rule
5. If no rule found, return RATE_RULE_NOT_FOUND warning
```

### 4.3 Missing Rule Behaviour

If no active rule is found:

```text
Do not silently calculate using zero
Return warning: RATE_RULE_NOT_FOUND
Require manager approval
Allow manual override only with reason
Store missing rule warning in calculation snapshot
```

---

## 5. Labour Calculation Logic

Labour is usually the largest part of the estimate. It must support:

```text
Hourly work
Half-day work
Full-day work
Multiple engineers
Labourer/helper support
Manual rate override
Minimum hours
Minimum charge
Out-of-hours future
Weekend/emergency future
```

---

### 5.1 Hourly Engineer Labour

```text
Engineer Labour Total =
Number of Engineers × Hours On Site × Engineer Hourly Rate
```

Example:

```text
1 engineer × 2 hours × £75 = £150
```

Backend formula key:

```text
engineer_labour_total = engineers * hours * hourly_rate
```

---

### 5.2 Hourly Labourer / Helper Labour

If labourer/helper is included:

```text
Labourer Total =
Number of Labourers × Hours On Site × Labourer Hourly Rate
```

Example:

```text
1 labourer × 2 hours × £40 = £80
```

---

### 5.3 Combined Hourly Labour

```text
Labour Total =
Engineer Labour Total + Labourer Total
```

Example:

```text
Engineer Labour = £150
Labourer Labour = £80
Total Labour = £230
```

---

### 5.4 Half-Day Labour

```text
Half-Day Labour Total =
Number of Engineers × Half-Day Rate
```

If labourers are included:

```text
Half-Day Labour Total =
(Number of Engineers × Engineer Half-Day Rate)
+ (Number of Labourers × Labourer Half-Day Rate)
```

---

### 5.5 Full-Day Labour

```text
Day Labour Total =
Number of Engineers × Days On Site × Day Rate
```

If labourers are included:

```text
Day Labour Total =
(Number of Engineers × Days On Site × Engineer Day Rate)
+ (Number of Labourers × Days On Site × Labourer Day Rate)
```

---

### 5.6 Labour Type Logic

```text
If labour_type = hourly:
    use hours_on_site and hourly_rate

If labour_type = half_day:
    use half_day_rate

If labour_type = day:
    use days_on_site and day_rate
```

---

### 5.7 Minimum Hours Logic

Some clients/trades may require minimum billable hours.

```text
Billable Hours =
max(Actual Hours, Minimum Hours)
```

Then:

```text
Hourly Labour Total =
Number of Engineers × Billable Hours × Hourly Rate
```

Example:

```text
Actual hours = 1
Minimum hours = 2
Hourly rate = £75

Billable hours = 2
Labour total = 1 × 2 × £75 = £150
```

---

### 5.8 Minimum Charge Logic

Some clients/trades may require minimum charge.

```text
Final Labour Total =
max(Calculated Labour Total, Minimum Charge)
```

Example:

```text
Calculated labour = £80
Minimum charge = £120

Final labour = £120
```

---

### 5.9 Manual Labour Rate Override

Manual override should only be allowed if:

```text
User role = Estimator / Manager / Admin
Override reason is provided
Quote requires manager approval
Audit log is created
Calculation snapshot stores override
```

Formula:

```text
If manual_override = true:
    Rate Used = Manual Labour Rate
Else:
    Rate Used = Matched Rule Rate
```

Approval:

```text
Manual Override Used = Approval Required
```

---

### 5.10 Labour Formula Output

Internal formula breakdown must include:

```json
{
  "labour_formula": "1 engineer × 2 hours × £75",
  "engineer_count": 1,
  "hours": 2,
  "rate_used": 75,
  "labour_total": 150,
  "minimum_hours_applied": false,
  "minimum_charge_applied": false,
  "manual_override_used": false
}
```

---

## 6. Material Calculation Logic

Materials must support:

```text
Quantity
Unit cost
Delivery cost
Percentage markup
Fixed markup
No markup
Supplier link
Internal-only supplier cost
Client-visible summary
```

---

### 6.1 Material Base Cost

```text
Material Base Cost =
Quantity × Unit Cost + Delivery Cost
```

Example:

```text
1 × £82.49 + £0 = £82.49
```

---

### 6.2 Percentage Markup

```text
Material Markup =
Material Base Cost × Markup Percentage
```

```text
Material Sell Total =
Material Base Cost + Material Markup
```

Example:

```text
Base cost = £82.49
Markup = 20%

Markup total = £82.49 × 20% = £16.50
Sell total = £82.49 + £16.50 = £98.99
```

---

### 6.3 Fixed Markup

```text
Material Sell Total =
Material Base Cost + Fixed Markup
```

Example:

```text
Base cost = £82.49
Fixed markup = £10

Sell total = £92.49
```

---

### 6.4 No Markup

```text
Material Sell Total =
Material Base Cost
```

---

### 6.5 Multiple Materials

```text
Material Sell Total =
Sum of all material line sell totals
```

Example:

```text
Material 1 sell total = £98.99
Material 2 sell total = £45.00

Total material sell = £143.99
```

---

### 6.6 Material Supplier Discount

Optional future logic:

```text
Discounted Unit Cost =
Unit Cost - Supplier Discount
```

or:

```text
Discounted Unit Cost =
Unit Cost × (1 - Supplier Discount Percentage)
```

Then:

```text
Material Base Cost =
Quantity × Discounted Unit Cost + Delivery Cost
```

---

### 6.7 Material VAT Handling

Default MVP:

```text
VAT is applied at quote subtotal level.
Do not calculate separate material VAT unless configured.
```

Future:

```text
Material VAT can be enabled per material line or client rule.
```

---

### 6.8 Material Formula Output

Internal formula breakdown must include:

```json
{
  "material_name": "Hafele Pull Down Wardrobe Rail",
  "quantity": 1,
  "unit_cost": 82.49,
  "delivery_cost": 0,
  "base_cost": 82.49,
  "markup_type": "percentage",
  "markup_value": 20,
  "markup_total": 16.50,
  "sell_total": 98.99,
  "formula": "1 × £82.49 + £0 delivery + 20% markup"
}
```

---

## 7. Parking Calculation Logic

Parking must support multiple modes because some jobs have actual parking, hourly parking, included parking, or non-chargeable parking.

---

### 7.1 Parking Types

Allowed values:

```text
hourly
fixed
actual
included
not_chargeable
```

---

### 7.2 Hourly Parking

```text
Parking Total =
Parking Rate Per Hour × Parking Hours
```

Example:

```text
£6.50 × 2 hours = £13.00
```

---

### 7.3 Fixed Parking

```text
Parking Total =
Parking Fixed Amount
```

---

### 7.4 Actual Parking

```text
Parking Total =
Actual Parking Cost
```

This is usually entered manually after site visit.

---

### 7.5 Included Parking

```text
Parking Total = £0
```

Use when parking is included in labour/rate.

---

### 7.6 Not Chargeable Parking

```text
Parking Total = £0
```

Use when parking is not passed to client.

---

### 7.7 Parking Markup

Optional rule:

```text
If parking markup type = percentage:
    Parking Client Charge = Parking Cost × (1 + Markup Percentage)

If parking markup type = fixed:
    Parking Client Charge = Parking Cost + Fixed Markup

If no markup:
    Parking Client Charge = Parking Cost
```

MVP recommendation:

```text
Parking is passed through at cost unless client rule says otherwise.
```

---

### 7.8 Parking Cap

Optional rule:

```text
Parking Client Charge =
min(Calculated Parking Charge, Parking Cap)
```

---

### 7.9 Parking Formula Output

```json
{
  "parking_type": "hourly",
  "parking_rate_per_hour": 6.5,
  "parking_hours": 2,
  "parking_total": 13,
  "formula": "£6.50 × 2 hours"
}
```

---

## 8. Congestion Charge Logic

### 8.1 Congestion Required

```text
If congestion_required = true:
    congestion_total = congestion_amount
Else:
    congestion_total = 0
```

---

### 8.2 Congestion Chargeable to Client

```text
If congestion_chargeable_to_client = true:
    Add congestion_total to subtotal
Else:
    Internal cost only, do not add to client subtotal
```

---

### 8.3 Congestion Included in Labour

If client rule says congestion is included:

```text
congestion_total = 0
```

but store internal note:

```text
Congestion included in labour/rate
```

---

### 8.4 Congestion Formula Output

```json
{
  "congestion_required": true,
  "chargeable_to_client": true,
  "congestion_amount": 15,
  "formula": "Congestion charge applied: £15"
}
```

---

## 9. ULEZ Logic

### 9.1 ULEZ Required

```text
If ulez_required = true:
    ulez_total = ulez_amount
Else:
    ulez_total = 0
```

### 9.2 ULEZ Chargeable to Client

```text
If ulez_chargeable_to_client = true:
    Add ulez_total to subtotal
Else:
    Internal cost only, do not add to client subtotal
```

---

## 10. Waste Disposal Logic

### 10.1 Waste Disposal Required

```text
If waste_disposal_required = true:
    waste_disposal_total = waste_disposal_amount
Else:
    waste_disposal_total = 0
```

### 10.2 Waste Disposal Approval

Require approval if:

```text
waste_disposal_amount > configured threshold
```

---

## 11. Travel Charge Logic

Travel time and travel charge are separate.

### 11.1 Travel Time

```text
travel_time_minutes
```

This is stored for internal use and can be used in future rules.

### 11.2 Travel Charge

If travel is chargeable:

```text
Travel Total = Travel Charge
```

MVP:

```text
Travel charge is manually entered.
```

Future:

```text
Travel Charge = Travel Time Hours × Travel Hourly Rate
```

---

## 12. Other Charges Logic

### 12.1 Other Charge

```text
Other Charge Total = other_charge
```

### 12.2 Other Charge Validation

If `other_charge > 0`, then:

```text
other_charge_reason is required
```

### 12.3 Other Charge Approval

If other charge is added:

```text
Approval may be required based on client/system rule
```

---

## 13. Subtotal Logic

```text
Subtotal =
Labour Total
+ Material Sell Total
+ Parking Client Charge
+ Congestion Client Charge
+ ULEZ Client Charge
+ Waste Disposal Total
+ Travel Charge
+ Other Charge
```

---

## 14. VAT Logic

VAT rules must be configurable.

---

### 14.1 Default VAT

```text
VAT Total =
Subtotal × VAT Rate
```

Example:

```text
Subtotal = £261.99
VAT rate = 20%

VAT = £261.99 × 20% = £52.40
```

---

### 14.2 VAT Included vs Excluded

Default MVP:

```text
VAT is excluded from subtotal and added at the end.
```

Optional future:

```text
If prices include VAT:
    Net Amount = Gross Amount / (1 + VAT Rate)
    VAT Amount = Gross Amount - Net Amount
```

---

### 14.3 VAT Exempt Client

If client is VAT exempt:

```text
VAT Total = 0
```

but store:

```text
VAT exemption reason
```

---

### 14.4 VAT Per Charge Type

Default MVP:

```text
Apply VAT to full subtotal.
```

Future configuration:

```text
VAT on labour: yes/no
VAT on materials: yes/no
VAT on parking: yes/no
VAT on congestion: yes/no
VAT on waste disposal: yes/no
```

---

### 14.5 Reverse Charge VAT

Future rule:

```text
If reverse_charge = true:
    VAT Total = 0
    Show reverse charge note on client quote
```

---

## 15. Final Total Logic

```text
Final Total =
Subtotal + VAT Total
```

---

## 16. Margin Logic

Margin is internal only.

### 16.1 Internal Cost

```text
Internal Cost =
Engineer Cost
+ Labourer Cost
+ Material Base Cost
+ Parking Internal Cost
+ Congestion Internal Cost
+ ULEZ Internal Cost
+ Waste Disposal Internal Cost
+ Other Internal Cost
```

### 16.2 Margin Amount

```text
Margin Amount =
Subtotal - Internal Cost
```

### 16.3 Margin Percentage

```text
Margin Percentage =
(Margin Amount / Subtotal) × 100
```

### 16.4 Margin Approval Rule

```text
If Margin Percentage < Minimum Margin Percentage:
    Approval Required
```

---

## 17. Rounding Logic

### 17.1 Money Rounding

All currency values must be rounded to 2 decimal places.

```text
round(value, 2)
```

### 17.2 Labour Hour Rounding

Configurable:

```text
none
nearest_0_25
nearest_0_5
nearest_1
always_up_0_5
always_up_1
```

Recommended MVP:

```text
nearest_0_5 or always_up_0_5 based on business rule
```

### 17.3 VAT Rounding

```text
VAT Total = round(VAT Total, 2)
```

### 17.4 Final Quote Rounding

Optional:

```text
If round_final_to_nearest_pound = true:
    Final Total = round(Final Total, 0)
```

Default MVP:

```text
Do not round final total to whole pounds unless enabled.
```

---

## 18. Approval Requirement Logic

The engine must return:

```json
{
  "requires_approval": true,
  "approval_reasons": []
}
```

Approval is required if any of the following are true:

```text
Final total exceeds approval threshold
Margin percentage below minimum margin
Manual labour override used
Manual discount used
No active rate rule found
Material cost exceeds material threshold
Other charge added without reason
Labour hours exceed configured limit
Quote edited after approval
Rate rule is expired
VAT override used
Client-specific approval required
```

Example:

```json
{
  "requires_approval": true,
  "approval_reasons": [
    "Manual labour rate override used",
    "Margin below minimum threshold"
  ]
}
```

---

## 19. Revision and Recalculation Logic

### 19.1 Quote Edited Before Approval

```text
Status remains Draft or Calculated
Create new calculation snapshot
Audit log created
```

### 19.2 Quote Edited After Approval

```text
Status changes to Revision Required
Previous approval remains in history
Previous calculation snapshot remains unchanged
New calculation snapshot created
Existing final PDF becomes outdated
PDF must be regenerated after re-approval
```

### 19.3 PDF Regeneration

```text
If calculation changes after PDF generation:
    Mark old PDF as superseded
    Require new PDF generation
```

---

## 20. Calculation Snapshot

Every finalized calculation must save:

```json
{
  "quote_id": "uuid",
  "input_snapshot": {
    "labour": {},
    "materials": [],
    "charges": {}
  },
  "rule_snapshot": {
    "rule_id": "uuid",
    "rule_version": "client_trade_v1",
    "hourly_rate": 75,
    "vat_rate": 20
  },
  "output_snapshot": {
    "labour_total": 150,
    "material_sell_total": 98.99,
    "parking_total": 13,
    "subtotal": 261.99,
    "vat_total": 52.40,
    "final_total": 314.39,
    "requires_approval": false
  },
  "formula_breakdown": {},
  "calculated_by": "user_id",
  "calculated_at": "timestamp"
}
```

---

## 21. Formula Breakdown Response

Calculation API must return:

```json
{
  "formula_breakdown": {
    "labour": "1 engineer × 2 hours × £75 = £150.00",
    "materials": "1 × £82.49 + 20% markup = £98.99",
    "parking": "£6.50 × 2 hours = £13.00",
    "congestion": "No congestion charge = £0.00",
    "ulez": "No ULEZ charge = £0.00",
    "vat": "£261.99 × 20% = £52.40",
    "final": "£261.99 + £52.40 = £314.39"
  }
}
```

---

## 22. Full Calculation API Example

### 22.1 Request

```json
{
  "job_id": "job_uuid",
  "client_id": "client_uuid",
  "trade_id": "trade_uuid",
  "quote_date": "2026-05-24",
  "labour": {
    "labour_type": "hourly",
    "number_of_engineers": 1,
    "number_of_labourers": 0,
    "hours_on_site": 2,
    "days_on_site": 0,
    "manual_override": false
  },
  "materials": [
    {
      "material_name": "Hafele Pull Down Wardrobe Rail",
      "supplier_link": "https://example.com/product",
      "quantity": 1,
      "unit_cost": 82.49,
      "delivery_cost": 0,
      "markup_type": "percentage",
      "markup_value": 20
    }
  ],
  "charges": {
    "parking_required": true,
    "parking_type": "hourly",
    "parking_rate_per_hour": 6.5,
    "parking_hours": 2,
    "parking_fixed_amount": 0,
    "congestion_required": false,
    "congestion_amount": 0,
    "congestion_chargeable_to_client": true,
    "ulez_required": false,
    "ulez_amount": 0,
    "ulez_chargeable_to_client": true,
    "waste_disposal_required": false,
    "waste_disposal_amount": 0,
    "travel_charge": 0,
    "other_charge": 0,
    "other_charge_reason": null
  }
}
```

### 22.2 Response

```json
{
  "success": true,
  "data": {
    "rule_version": "napier_watt_handyman_v1",
    "formula_version": "formula_v1",
    "labour": {
      "engineer_labour_total": 150,
      "labourer_labour_total": 0,
      "labour_total": 150,
      "formula": "1 engineer × 2 hours × £75"
    },
    "materials": {
      "items": [
        {
          "material_name": "Hafele Pull Down Wardrobe Rail",
          "base_cost": 82.49,
          "markup_total": 16.50,
          "sell_total": 98.99,
          "formula": "1 × £82.49 + 20% markup"
        }
      ],
      "material_base_total": 82.49,
      "material_markup_total": 16.50,
      "material_sell_total": 98.99
    },
    "charges": {
      "parking_total": 13,
      "congestion_total": 0,
      "ulez_total": 0,
      "waste_disposal_total": 0,
      "travel_charge": 0,
      "other_charge": 0
    },
    "subtotal": 261.99,
    "vat_rate": 20,
    "vat_total": 52.40,
    "final_total": 314.39,
    "requires_approval": false,
    "approval_reasons": [],
    "warnings": [],
    "formula_breakdown": {
      "labour": "1 engineer × 2 hours × £75 = £150.00",
      "materials": "1 × £82.49 + 20% markup = £98.99",
      "parking": "£6.50 × 2 hours = £13.00",
      "congestion": "No congestion charge = £0.00",
      "vat": "£261.99 × 20% = £52.40",
      "final": "£261.99 + £52.40 = £314.39"
    }
  }
}
```

---

## 23. Validation Rules

### 23.1 Labour Validation

```text
trade_id is required
labour_type is required
number_of_engineers must be >= 0
number_of_labourers must be >= 0
At least one engineer or labourer is required
If labour_type = hourly, hours_on_site must be > 0
If labour_type = day, days_on_site must be > 0
Manual override requires manual rate and reason
```

### 23.2 Material Validation

```text
material_name is required if material line exists
quantity must be > 0
unit_cost must be >= 0
delivery_cost must be >= 0
supplier_link must be valid URL if provided
markup_value must be >= 0
```

### 23.3 Charges Validation

```text
If parking_required = true, parking_type is required
If parking_type = hourly, rate and hours are required
If congestion_required = true, congestion_amount is required
If ulez_required = true, ulez_amount is required
If waste_disposal_required = true, waste_disposal_amount is required
If other_charge > 0, other_charge_reason is required
```

---

## 24. Unit Test Cases

Create file:

```text
backend/tests/unit/test_calculation_engine.py
```

Required tests:

```text
test_hourly_labour_single_engineer
test_hourly_labour_multiple_engineers
test_hourly_labour_with_labourer
test_half_day_labour
test_day_labour
test_minimum_hours_applied
test_minimum_charge_applied
test_manual_labour_override
test_manual_override_requires_approval
test_material_markup_percentage
test_material_markup_fixed
test_material_no_markup
test_material_delivery_cost_added
test_multiple_materials_total
test_parking_hourly
test_parking_fixed
test_parking_actual
test_parking_included
test_parking_not_chargeable
test_parking_markup_percentage
test_parking_cap_applied
test_congestion_yes_chargeable
test_congestion_yes_not_chargeable
test_congestion_no
test_ulez_yes_chargeable
test_ulez_yes_not_chargeable
test_ulez_no
test_waste_disposal_added
test_travel_charge_added
test_other_charge_added
test_other_charge_requires_reason
test_vat_default
test_vat_exempt_client
test_vat_included_future
test_subtotal_calculation
test_final_total_calculation
test_margin_calculation
test_low_margin_requires_approval
test_high_total_requires_approval
test_no_rate_rule_requires_approval
test_round_money_to_two_decimals
test_round_labour_hours_nearest_half
test_quote_edit_after_approval_requires_revision
```

---

## 25. Regression Test Cases

### 25.1 Regression Case A — Basic Hourly Estimate

Input:

```text
Engineers = 1
Hours = 2
Hourly Rate = £75
Material = 1 × £82.49
Material Markup = 20%
Parking = £6.50 × 2
Congestion = No
ULEZ = No
VAT = 20%
```

Expected:

```text
Labour = £150.00
Material Base = £82.49
Material Markup = £16.50
Material Sell = £98.99
Parking = £13.00
Subtotal = £261.99
VAT = £52.40
Final = £314.39
```

---

### 25.2 Regression Case B — Congestion Yes

Input:

```text
Same as Case A
Congestion = £15
VAT = 20%
```

Expected:

```text
Subtotal = £276.99
VAT = £55.40
Final = £332.39
```

---

### 25.3 Regression Case C — Minimum Charge

Input:

```text
Engineers = 1
Hours = 1
Hourly rate = £50
Minimum charge = £120
```

Expected:

```text
Labour = £120
minimum_charge_applied = true
```

---

### 25.4 Regression Case D — Labourer Added

Input:

```text
Engineer = 1
Labourer = 1
Hours = 2
Engineer rate = £75
Labourer rate = £40
```

Expected:

```text
Engineer labour = £150
Labourer labour = £80
Labour total = £230
```

---

### 25.5 Regression Case E — Parking Not Chargeable

Input:

```text
Parking required = true
Parking type = not_chargeable
Parking actual cost = £20
```

Expected:

```text
Parking client charge = £0
Parking internal cost = £20
```

---

## 26. Pseudocode for Calculation Engine

```python
def calculate_quote(input_data, rule):
    warnings = []
    approval_reasons = []

    labour_result = calculate_labour(input_data.labour, rule)
    material_result = calculate_materials(input_data.materials, rule)
    charge_result = calculate_charges(input_data.charges, rule)

    subtotal = (
        labour_result.total
        + material_result.sell_total
        + charge_result.client_charge_total
    )

    vat_total = calculate_vat(subtotal, rule)

    final_total = subtotal + vat_total

    margin_result = calculate_margin(
        subtotal=subtotal,
        internal_cost=(
            labour_result.internal_cost
            + material_result.base_total
            + charge_result.internal_cost_total
        )
    )

    if final_total > rule.approval_threshold:
        approval_reasons.append("Quote total exceeds approval threshold")

    if margin_result.percentage < rule.minimum_margin_percentage:
        approval_reasons.append("Margin below minimum threshold")

    if labour_result.manual_override_used:
        approval_reasons.append("Manual labour override used")

    if rule.is_missing:
        warnings.append("No active rate rule found")
        approval_reasons.append("No active rate rule found")

    return CalculationResult(
        labour=labour_result,
        materials=material_result,
        charges=charge_result,
        subtotal=round_money(subtotal),
        vat_total=round_money(vat_total),
        final_total=round_money(final_total),
        margin=margin_result,
        requires_approval=len(approval_reasons) > 0,
        approval_reasons=approval_reasons,
        warnings=warnings,
        formula_breakdown=build_formula_breakdown(...)
    )
```

---

## 27. Cursor Instruction

Use this instruction in Cursor:

```text
Implement the calculation engine exactly based on this formula specification.

Rules:
- Calculation must run on backend only.
- Do not hardcode client pricing.
- Use client + trade + active date rule lookup.
- Return detailed formula breakdown.
- Store calculation snapshots.
- Add unit tests for every formula.
- Add regression tests using sample cases.
- Client view must not expose supplier cost, markup, margin, formula breakdown, or internal notes.
- Manual override must require reason and manager approval.
- Missing rate rule must not silently calculate.
- Every finalized quote must be repeatable using stored rule snapshot.
```

---

## 28. Final Notes

This formula specification should be treated as the source of truth for calculation implementation.

Before production release, compare calculated results against the existing Excel quote calculator for:

```text
Client + Trade combinations
Hourly formulas
Day formulas
Material markup
Parking
Congestion
VAT
Minimum charge
Rounding
```

Any Excel-specific formula discovered later should be added to this document as a new version.
