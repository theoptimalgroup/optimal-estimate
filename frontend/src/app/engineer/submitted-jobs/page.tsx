import Link from "next/link";

import { PageHeader, PrimaryButton, SectionCard } from "@/components/ui";

export default function EngineerSubmittedJobsPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6" data-testid="engineer-submitted-jobs-page">
      <PageHeader
        title="Submitted Jobs"
        description="Track jobs you have completed and submitted."
      />

      <SectionCard testId="engineer-submitted-jobs-empty">
        <div className="space-y-4" data-testid="engineer-no-submitted-jobs">
          <p className="text-sm text-slate-600">No submitted jobs yet.</p>
          <p className="text-sm text-slate-600">
            Submitted jobs will appear here after you complete assigned jobs.
          </p>
          <Link href="/engineer/assigned-jobs">
            <PrimaryButton data-testid="engineer-submitted-jobs-go-jobs">Go to Assigned Jobs</PrimaryButton>
          </Link>
        </div>
      </SectionCard>
    </div>
  );
}
