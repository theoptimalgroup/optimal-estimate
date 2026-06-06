"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { RequireRole } from "@/components/auth/require-role";
import { ErrorState, LoadingState, PrimaryButton, SecondaryButton } from "@/components/ui";
import { createManualEstimateSession } from "@/lib/manual-estimate";

function NewEstimateRedirect() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    void (async () => {
      try {
        const result = await createManualEstimateSession();
        router.replace(result.resume_url);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create estimate");
      }
    })();
  }, [router]);

  if (error) {
    return (
      <div className="w-full max-w-md space-y-4" data-testid="new-estimate-error">
        <ErrorState message={error} />
        <PrimaryButton onClick={() => window.location.reload()}>Try again</PrimaryButton>
        <SecondaryButton onClick={() => router.back()}>Go back</SecondaryButton>
      </div>
    );
  }

  return <LoadingState message="Creating estimate…" />;
}

export default function NewEstimatePage() {
  return (
    <RequireRole allowedRoles={["admin", "manager", "estimator"]}>
      <div
        className="flex min-h-screen items-center justify-center bg-slate-50 px-4"
        data-testid="new-estimate-page"
      >
        <NewEstimateRedirect />
      </div>
    </RequireRole>
  );
}
