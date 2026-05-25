import type { ChangeEvent } from "react";
import type { UseFormRegisterReturn } from "react-hook-form";

/** Keep React Hook Form in sync when adding custom onChange side effects. */
export function withRegisterChange<T extends HTMLElement>(
  field: UseFormRegisterReturn,
  handler?: (event: ChangeEvent<T>) => void,
): UseFormRegisterReturn {
  return {
    ...field,
    onChange: (event) => {
      const result = field.onChange(event);
      handler?.(event as ChangeEvent<T>);
      return result;
    },
  };
}

export function formatFieldError(message?: string): string | undefined {
  if (!message) return undefined;
  if (message === "Invalid input" || message.startsWith("Invalid input:")) {
    return "Enter a valid value";
  }
  return message;
}
