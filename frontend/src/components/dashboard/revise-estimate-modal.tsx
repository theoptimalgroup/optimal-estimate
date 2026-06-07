"use client";

import { useState } from "react";

import { EworksButton, EworksInput, EworksLabel } from "@/components/eworks-ui";

type ReviseEstimateModalProps = {
  open: boolean;
  loading?: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: (reason: string) => void | Promise<void>;
};

export function ReviseEstimateModal({
  open,
  loading,
  error,
  onCancel,
  onConfirm,
}: ReviseEstimateModalProps) {
  const [reason, setReason] = useState("");

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4" data-testid="revise-estimate-modal">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-5 shadow-xl">
        <h2 className="text-lg font-semibold text-slate-900">Revise Estimate</h2>
        <p className="mt-2 text-sm text-slate-600">
          Provide a reason for this revision. The current submission will be preserved in version history.
        </p>
        <form
          className="mt-4 space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            void onConfirm(reason.trim());
          }}
        >
          <EworksLabel>
            Reason
            <EworksInput
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Describe why this estimate needs revision"
              required
              data-testid="revise-estimate-reason"
            />
          </EworksLabel>
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          <div className="flex justify-end gap-3">
            <EworksButton type="button" variant="secondary" onClick={onCancel} disabled={loading}>
              Cancel
            </EworksButton>
            <EworksButton type="submit" disabled={loading || !reason.trim()} data-testid="revise-estimate-confirm">
              {loading ? "Unlocking…" : "Unlock for Revision"}
            </EworksButton>
          </div>
        </form>
      </div>
    </div>
  );
}
