"use client";

import type { ControllerRenderProps } from "react-hook-form";
import { Controller } from "react-hook-form";
import type { Control, FieldErrors, FieldPath, UseFormRegister, UseFormSetValue } from "react-hook-form";
import {
  EworksButton,
  EworksCheckbox,
  EworksFieldError,
  EworksInput,
  EworksLabel,
  EworksTextarea,
  eworksInputClass,
} from "@/components/eworks-ui";
import type { QuestionnaireFormValues } from "@/lib/eworks-calculate-schema";
import { useState, type InputHTMLAttributes } from "react";

function NumericInput({
  field,
  hasError,
  placeholder,
  className,
  ...rest
}: {
  field: ControllerRenderProps<QuestionnaireFormValues, FieldPath<QuestionnaireFormValues>>;
  hasError?: boolean;
  placeholder?: string;
  className?: string;
} & Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "onBlur" | "name">) {
  const [editing, setEditing] = useState<string | null>(null);
  const numericValue = field.value as number | undefined;
  const displayValue =
    editing !== null
      ? editing
      : typeof numericValue === "number" && !Number.isNaN(numericValue)
        ? String(numericValue)
        : "";

  return (
    <EworksInput
      type="text"
      inputMode="decimal"
      placeholder={placeholder}
      hasError={hasError}
      className={className}
      name={field.name}
      ref={field.ref}
      value={displayValue}
      onChange={(e) => {
        const raw = e.target.value;
        if (raw !== "" && !/^\d*\.?\d*$/.test(raw)) return;
        setEditing(raw);
        const parsed = raw === "" ? undefined : Number(raw);
        field.onChange(Number.isNaN(parsed as number) ? undefined : parsed);
      }}
      onBlur={() => {
        setEditing(null);
        field.onBlur();
      }}
      {...rest}
    />
  );
}

type Props = {
  control: Control<QuestionnaireFormValues>;
  register: UseFormRegister<QuestionnaireFormValues>;
  setValue: UseFormSetValue<QuestionnaireFormValues>;
  errors: FieldErrors<QuestionnaireFormValues>;
  values: QuestionnaireFormValues;
};

export function EworksAdditionalChargesForm({ control, register, setValue, errors, values }: Props) {
  const [gpsError, setGpsError] = useState<string | null>(null);
  const [capturingGps, setCapturingGps] = useState(false);

  const hasParkingGps = values.parking_latitude != null && values.parking_longitude != null;

  const captureParkingGps = () => {
    setGpsError(null);
    if (!navigator.geolocation) {
      setGpsError("Geolocation is not supported in this browser.");
      return;
    }
    setCapturingGps(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = Math.round(position.coords.latitude * 1_000_000) / 1_000_000;
        const lng = Math.round(position.coords.longitude * 1_000_000) / 1_000_000;
        setValue("parking_latitude", lat, { shouldValidate: true });
        setValue("parking_longitude", lng, { shouldValidate: true });
        setCapturingGps(false);
      },
      (error) => {
        setCapturingGps(false);
        if (error.code === error.PERMISSION_DENIED) {
          setGpsError("Location permission denied. Allow location access and try again.");
        } else {
          setGpsError("Could not capture location. Try again or enter coordinates manually.");
        }
      },
    );
  };

  const clearParkingGps = () => {
    setValue("parking_latitude", null, { shouldValidate: true });
    setValue("parking_longitude", null, { shouldValidate: true });
    setGpsError(null);
  };

  const openParkingInGoogleMaps = () => {
    const lat = values.parking_latitude;
    const lng = values.parking_longitude;
    if (lat == null || lng == null) return;
    window.open(`https://www.google.com/maps?q=${lat},${lng}`, "_blank", "noopener,noreferrer");
  };

  return (
    <section
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
      data-testid="additional-charges-section"
    >
      <h3 className="text-sm font-semibold text-slate-900">Additional Charges</h3>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <Controller
          name="parking_required"
          control={control}
          render={({ field }) => (
            <EworksCheckbox
              label="Parking charge"
              className="sm:col-span-2"
              name={field.name}
              ref={field.ref}
              checked={field.value === true}
              onBlur={field.onBlur}
              onChange={(e) => field.onChange(e.target.checked)}
            />
          )}
        />
        {values.parking_required && (
          <>
            <EworksLabel>
              Parking type
              <select className={eworksInputClass()} {...register("parking_type")}>
                <option value="fixed">Fixed</option>
                <option value="hourly">Hourly</option>
              </select>
            </EworksLabel>
            {values.parking_type === "hourly" ? (
              <>
                <EworksLabel>
                  Rate per hour (£)
                  <Controller
                    name="parking_rate_per_hour"
                    control={control}
                    render={({ field, fieldState }) => (
                      <>
                        <NumericInput field={field} hasError={!!fieldState.error} />
                        <EworksFieldError message={fieldState.error?.message} />
                      </>
                    )}
                  />
                </EworksLabel>
                <EworksLabel>
                  Hours
                  <Controller
                    name="parking_hours"
                    control={control}
                    render={({ field, fieldState }) => (
                      <>
                        <NumericInput field={field} hasError={!!fieldState.error} />
                        <EworksFieldError message={fieldState.error?.message} />
                      </>
                    )}
                  />
                </EworksLabel>
              </>
            ) : (
              <EworksLabel>
                Parking amount (£)
                <Controller
                  name="parking_fixed_amount"
                  control={control}
                  render={({ field, fieldState }) => (
                    <>
                      <NumericInput field={field} hasError={!!fieldState.error} />
                      <EworksFieldError message={fieldState.error?.message} />
                    </>
                  )}
                />
              </EworksLabel>
            )}
            <EworksLabel>
              Number of vehicles
              <Controller
                name="parking_vehicles"
                control={control}
                render={({ field, fieldState }) => (
                  <>
                    <EworksInput
                      type="text"
                      inputMode="numeric"
                      hasError={!!fieldState.error}
                      data-testid="quote-parking-vehicles"
                      name={field.name}
                      ref={field.ref}
                      value={String(field.value ?? 1)}
                      onChange={(e) => {
                        const raw = e.target.value.replace(/\D/g, "");
                        const parsed = raw === "" ? 1 : Math.max(1, parseInt(raw, 10));
                        field.onChange(parsed);
                      }}
                      onBlur={field.onBlur}
                    />
                    <EworksFieldError message={fieldState.error?.message} />
                  </>
                )}
              />
            </EworksLabel>
            <div className="space-y-3 sm:col-span-2" data-testid="quote-parking-gps">
              <p className="text-sm font-semibold text-slate-900">GPS snapshot</p>
              <div className="flex flex-wrap gap-2">
                <EworksButton
                  type="button"
                  variant="secondary"
                  className="min-h-[40px] text-xs"
                  disabled={capturingGps}
                  onClick={captureParkingGps}
                >
                  {capturingGps ? "Capturing…" : "Capture location"}
                </EworksButton>
                <EworksButton
                  type="button"
                  variant="secondary"
                  className="min-h-[40px] text-xs"
                  disabled={!hasParkingGps}
                  onClick={openParkingInGoogleMaps}
                >
                  Open in Google Maps
                </EworksButton>
                {hasParkingGps && (
                  <EworksButton type="button" variant="ghost" className="min-h-[40px] text-xs" onClick={clearParkingGps}>
                    Clear location
                  </EworksButton>
                )}
              </div>
              {hasParkingGps && (
                <p className="text-xs text-slate-600">
                  {values.parking_latitude}, {values.parking_longitude}
                </p>
              )}
              {gpsError && <EworksFieldError message={gpsError} />}
            </div>
            <EworksLabel className="sm:col-span-2">
              Parking notes
              <EworksTextarea rows={2} {...register("parking_notes")} data-testid="quote-parking-notes" />
            </EworksLabel>
          </>
        )}

        <Controller
          name="congestion_required"
          control={control}
          render={({ field }) => (
            <EworksCheckbox
              label="Congestion charge"
              className="sm:col-span-2"
              name={field.name}
              ref={field.ref}
              checked={field.value === true}
              onBlur={field.onBlur}
              onChange={(e) => field.onChange(e.target.checked)}
            />
          )}
        />
        {values.congestion_required && (
          <EworksLabel data-testid="quote-congestion-amount">
            Congestion amount (£)
            <Controller
              name="congestion_amount"
              control={control}
              render={({ field, fieldState }) => (
                <>
                  <NumericInput field={field} hasError={!!fieldState.error} />
                  <EworksFieldError message={fieldState.error?.message} />
                </>
              )}
            />
          </EworksLabel>
        )}

        <EworksLabel>
          Travel charge (£)
          <Controller
            name="travel_charge"
            control={control}
            render={({ field, fieldState }) => (
              <>
                <NumericInput field={field} hasError={!!fieldState.error} data-testid="quote-travel-charge" />
                <EworksFieldError message={fieldState.error?.message} />
              </>
            )}
          />
        </EworksLabel>

        <EworksLabel>
          Other charge (£)
          <Controller
            name="other_charge"
            control={control}
            render={({ field, fieldState }) => (
              <>
                <NumericInput field={field} hasError={!!fieldState.error} />
                <EworksFieldError message={fieldState.error?.message} />
              </>
            )}
          />
        </EworksLabel>

        {values.other_charge > 0 && (
          <EworksLabel className="sm:col-span-2">
            Other charge notes
            <EworksInput hasError={!!errors.other_charge_reason} {...register("other_charge_reason")} />
            <EworksFieldError message={errors.other_charge_reason?.message} />
          </EworksLabel>
        )}
      </div>
    </section>
  );
}
