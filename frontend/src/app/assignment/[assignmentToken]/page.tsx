"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ErrorState, LoadingState } from "@/components/ui";
import { startPublicAssignmentEstimate } from "@/lib/quote-assignments";

function formatPublicAssignmentError(error: unknown): string {
  if (!(error instanceof Error)) {
    return "This assignment link is invalid or has expired.";
  }
  const message = error.message.toLowerCase();
  if (
    message.includes("revoked") ||
    message.includes("expired") ||
    message.includes("cancelled") ||
    message.includes("410")
  ) {
    return "This assignment link is invalid or has expired.";
  }
  if (message.includes("not found") || message.includes("404")) {
    return "This assignment link is invalid or has expired.";
  }
  return error.message || "Failed to open estimate questionnaire.";
}

export default function PublicAssignmentPage({ params }: { params: { assignmentToken: string } }) {
  const router = useRouter();
  const { assignmentToken } = params;
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function redirectToQuestionnaire() {
      setError(null);
      try {
        const result = await startPublicAssignmentEstimate(assignmentToken);
        if (cancelled) return;
        router.replace(result.resume_url);
      } catch (e: unknown) {
        if (cancelled) return;
        setError(formatPublicAssignmentError(e));
      }
    }

    void redirectToQuestionnaire();
    return () => {
      cancelled = true;
    };
  }, [assignmentToken, router]);

  return (
    <div className="min-h-screen bg-slate-50" data-testid="public-assignment-page">
      <main className="mx-auto max-w-lg px-6 py-16">
        {error ? (
          <ErrorState message={error} />
        ) : (
          <LoadingState message="Preparing estimate questionnaire…" />
        )}
      </main>
    </div>
  );
}
