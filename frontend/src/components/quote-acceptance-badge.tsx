import { StatusBadge } from "@/components/ui";

export function QuoteAcceptanceBadge({ accepted }: { accepted: boolean }) {
  if (!accepted) {
    return <StatusBadge tone="neutral">Not accepted</StatusBadge>;
  }
  return (
    <span data-testid="quote-accepted-badge">
      <StatusBadge tone="success">Accepted</StatusBadge>
    </span>
  );
}
