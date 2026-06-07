"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EngineerAssignmentCard } from "@/components/engineer/engineer-assignment-card";
import { LoadingState, PageHeader, PrimaryButton, SectionCard } from "@/components/ui";
import { listMyQuoteAssignments, type QuoteAssignment } from "@/lib/quote-assignments";

export default function EngineerSubmittedEstimatesPage() {
  const [assignments, setAssignments] = useState<QuoteAssignment[]>([]);
  const [loading, setLoading] = useState(true);

  const loadAssignments = useCallback(async () => {
    setLoading(true);
    try {
      const items = await listMyQuoteAssignments();
      setAssignments(
        items.filter((item) => item.assignment_type === "engineer" && item.status === "submitted"),
      );
    } catch {
      setAssignments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAssignments();
  }, [loadAssignments]);

  return (
    <div className="mx-auto max-w-2xl space-y-6" data-testid="engineer-submitted-estimates-page">
      <PageHeader
        title="Submitted Estimates"
        description="Review estimates you have submitted for manager review."
      />

      <SectionCard title="Submitted Estimates" testId="engineer-submitted-quotes">
        {loading ? (
          <LoadingState message="Loading submitted estimates…" />
        ) : assignments.length === 0 ? (
          <div className="space-y-4" data-testid="engineer-no-submitted-estimates">
            <p className="text-sm text-slate-600">No submitted estimates yet.</p>
            <Link href="/engineer/assigned-estimates">
              <PrimaryButton data-testid="engineer-submitted-estimates-go-estimates">
                Go to Assigned Estimates
              </PrimaryButton>
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {assignments.map((item) => (
              <EngineerAssignmentCard
                key={item.id}
                assignment={item}
                variant="submitted"
                testIdPrefix="engineer-submitted"
              />
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
