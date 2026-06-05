"use client";

import { EworksButton } from "@/components/eworks-ui";

type Props = {
  open: boolean;
  onReplace: () => void;
  onKeep: () => void;
};

export function ScopeReplaceDialog({ open, onReplace, onKeep }: Props) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="scope-replace-title"
      data-testid="scope-replace-dialog"
    >
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-2xl">
        <h2 id="scope-replace-title" className="text-lg font-semibold text-slate-900">
          Replace existing scope?
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          Replace existing scope with selected product scope?
        </p>
        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <EworksButton type="button" variant="secondary" onClick={onKeep} data-testid="scope-replace-keep">
            Keep Current Scope
          </EworksButton>
          <EworksButton type="button" onClick={onReplace} data-testid="scope-replace-confirm">
            Replace Scope
          </EworksButton>
        </div>
      </div>
    </div>
  );
}
