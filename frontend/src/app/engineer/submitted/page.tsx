import { ComingSoonPage } from "@/components/layout/coming-soon-page";

export default function EngineerSubmittedPage() {
  return (
    <ComingSoonPage
      testId="engineer-submitted-placeholder"
      title="Submitted Jobs"
      message="Submitted job history will appear here. For now, open My Jobs to continue or review active site visits."
      primaryAction={{ label: "Go to My Jobs", href: "/engineer/jobs", testId: "engineer-submitted-go-jobs" }}
      workflowNote="Active and in-progress assignments remain in My Jobs until submitted job history is added here."
    />
  );
}
