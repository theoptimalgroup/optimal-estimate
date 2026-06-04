export function QuoteAcceptanceBadge({ accepted }: { accepted: boolean }) {
  if (!accepted) {
    return (
      <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
        Not accepted
      </span>
    );
  }
  return (
    <span
      className="inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800"
      data-testid="quote-accepted-badge"
    >
      Accepted
    </span>
  );
}
