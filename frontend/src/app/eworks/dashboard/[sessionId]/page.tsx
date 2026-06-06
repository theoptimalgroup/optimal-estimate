"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { QuoteReviewDetail } from "@/components/dashboard/quote-review-detail";
import { readDashboardPassword } from "@/lib/dashboard";
import { createPasswordDashboardClient } from "@/lib/dashboard-client";

export default function EworksDashboardQuotePage({
  params,
}: {
  params: { sessionId: string };
}) {
  const { sessionId } = params;
  const router = useRouter();
  const [password, setPassword] = useState<string | null>(null);

  useEffect(() => {
    const saved = readDashboardPassword();
    if (!saved) {
      router.replace("/eworks/dashboard");
      return;
    }
    setPassword(saved);
  }, [router]);

  const client = useMemo(
    () => (password ? createPasswordDashboardClient(password) : null),
    [password],
  );

  if (!client) {
    return null;
  }

  return (
    <QuoteReviewDetail
      sessionId={sessionId}
      client={client}
      backHref="/eworks/dashboard"
      listHref="/eworks/dashboard"
      shell="dashboard"
      showClientAcceptance
    />
  );
}
