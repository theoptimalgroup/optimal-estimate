"use client";

import { useCallback, useEffect, useState } from "react";

import { EngineerAssignedJobCard } from "@/components/engineer/engineer-assigned-job-card";
import { LoadingState, PageHeader, SectionCard } from "@/components/ui";
import { listEngineerAssignedJobs, type EngineerAssignedJob } from "@/lib/engineer-jobs";

export default function EngineerAssignedJobsPage() {
  const [jobs, setJobs] = useState<EngineerAssignedJob[]>([]);
  const [loading, setLoading] = useState(true);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    try {
      setJobs(await listEngineerAssignedJobs());
    } catch {
      setJobs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  return (
    <div className="mx-auto max-w-2xl space-y-6" data-testid="engineer-assigned-jobs-page">
      <PageHeader
        title="Assigned Jobs"
        description="Jobs where your estimate was selected by a manager."
      />

      <SectionCard title="Assigned Jobs" testId="engineer-assigned-jobs-list">
        {loading ? (
          <LoadingState message="Loading assigned jobs…" />
        ) : jobs.length === 0 ? (
          <p className="text-sm text-slate-600" data-testid="engineer-no-assigned-jobs">
            No assigned jobs yet.
          </p>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => (
              <EngineerAssignedJobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
