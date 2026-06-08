"use client";

import { EworksButton } from "@/components/eworks-ui";

type Props = {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  testId?: string;
};

export function WorkModeSwitchDialog({
  open,
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
  testId = "work-mode-switch-dialog",
}: Props) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="work-mode-switch-title"
      data-testid={testId}
    >
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-2xl">
        <h2 id="work-mode-switch-title" className="text-lg font-semibold text-slate-900">
          {title}
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">{message}</p>
        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <EworksButton type="button" variant="secondary" onClick={onCancel} data-testid={`${testId}-cancel`}>
            Cancel
          </EworksButton>
          <EworksButton type="button" onClick={onConfirm} data-testid={`${testId}-confirm`}>
            {confirmLabel}
          </EworksButton>
        </div>
      </div>
    </div>
  );
}
