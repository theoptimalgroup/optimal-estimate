import { ComingSoonPage } from "@/components/layout/coming-soon-page";

export default function EngineerUploadsPage() {
  return (
    <ComingSoonPage
      testId="engineer-uploads-placeholder"
      title="Upload Photos"
      message="Photos are currently uploaded from the job detail page so they stay attached to the correct site visit."
      primaryAction={{ label: "Go to My Jobs", href: "/engineer/jobs", testId: "engineer-uploads-go-jobs" }}
      workflowNote="Select a job in My Jobs, then upload photos from the job detail view."
    />
  );
}
