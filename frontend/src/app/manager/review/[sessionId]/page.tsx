"use client";

import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { QuoteReviewDetail } from "@/components/dashboard/quote-review-detail";
import { createRoleDashboardClient } from "@/lib/dashboard-client";
import type { ReopenQuoteResponse } from "@/lib/dashboard";

export default function ManagerReviewSessionPage({
  params,
}: {
  params: { sessionId: string };
}) {
  const { sessionId } = params;
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
      client={client}
      backHref="/manager/review"
      listHref="/manager/review"
      onUnlockSuccess={handleUnlockSuccess}
      shell="embedded"
      enableClientLink
    />
  );
}
