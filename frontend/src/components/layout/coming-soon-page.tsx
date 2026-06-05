import Link from "next/link";

import { PageHeader, PrimaryButton, SecondaryButton, SectionCard } from "@/components/ui";

export type ComingSoonAction = {
  label: string;
  href: string;
  testId?: string;
};

type ComingSoonPageProps = {
  title: string;
  message: string;
  primaryAction: ComingSoonAction;
  secondaryAction?: ComingSoonAction;
  workflowNote: string;
  testId?: string;
};

export function ComingSoonPage({
  title,
  message,
  primaryAction,
  secondaryAction,
  workflowNote,
  testId,
}: ComingSoonPageProps) {
  return (
    <div className="space-y-6" data-testid={testId}>
      <PageHeader title={title} description={message} />
      <SectionCard>
        <div className="space-y-5">
          <p className="text-sm leading-relaxed text-slate-600">{workflowNote}</p>
          <div className="flex flex-wrap gap-3">
            <Link href={primaryAction.href}>
              <PrimaryButton data-testid={primaryAction.testId ?? "coming-soon-primary"}>
                {primaryAction.label}
              </PrimaryButton>
            </Link>
            {secondaryAction ? (
              <Link href={secondaryAction.href}>
                <SecondaryButton data-testid={secondaryAction.testId ?? "coming-soon-secondary"}>
                  {secondaryAction.label}
                </SecondaryButton>
              </Link>
            ) : null}
          </div>
        </div>
      </SectionCard>
    </div>
  );
}
