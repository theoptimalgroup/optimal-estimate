"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo } from "react";
import { QuoteReviewDetail } from "@/components/dashboard/quote-review-detail";
import { LoadingState } from "@/components/ui";
import { createRoleDashboardClient } from "@/lib/dashboard-client";
import type { ReopenQuoteResponse } from "@/lib/dashboard";

function ManagerReviewSessionContent({ sessionId }: { sessionId: string }) {
  const searchParams = useSearchParams();
  const versionRaw = searchParams.get("version");
  const versionNumber = versionRaw ? Number.parseInt(versionRaw, 10) : undefined;
  const router = useRouter();
  const client = useMemo(() => createRoleDashboardClient(), []);

  const handleUnlockSuccess = (reopened: ReopenQuoteResponse) => {
    const search = new URLSearchParams({
      session_id: reopened.session_id,
      token: reopened.session_token,
    });
    router.push(`/eworks/calculate?${search.toString()}`);
  };

  return (
    <QuoteReviewDetail
      sessionId={sessionId}
      versionNumber={Number.isFinite(versionNumber) ? versionNumber : undefined}
      client={client}
      backHref="/manager/review"
      listHref="/manager/review"
      onUnlockSuccess={handleUnlockSuccess}
      shell="embedded"
    />
  );
}

export default function ManagerReviewSessionPage({
  params,
}: {
  params: { sessionId: string };
}) {
  const { sessionId } = params;

  return (
    <Suspense fallback={<LoadingState message="Loading submission…" />}>
      <ManagerReviewSessionContent sessionId={sessionId} />
    </Suspense>
  );
}
