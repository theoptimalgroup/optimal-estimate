import { ComingSoonPage } from "@/components/layout/coming-soon-page";

export default function EngineerSiteNotesPage() {
  return (
    <ComingSoonPage
      testId="engineer-site-notes-placeholder"
      title="Site Visit Notes"
      message="Site notes are currently captured inside each assigned job."
      primaryAction={{ label: "Go to My Jobs", href: "/engineer/jobs", testId: "engineer-site-notes-go-jobs" }}
      workflowNote="Open a job from My Jobs to add or review site visit notes for that assignment."
    />
  );
}
