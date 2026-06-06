import { StatusBadge } from "@/components/ui/status-badge";
import { cn } from "@/lib/utils";

const MAX_TAG_LENGTH = 18;

function truncateTag(tag: string): string {
  return tag.length > MAX_TAG_LENGTH ? `${tag.slice(0, MAX_TAG_LENGTH)}…` : tag;
}

export function TagBadges({
  tags,
  maxVisible = 2,
  compact = false,
  emptyLabel = "—",
  className,
}: {
  tags?: string[];
  maxVisible?: number;
  compact?: boolean;
  emptyLabel?: string;
  className?: string;
}) {
  if (!tags?.length) {
    if (!emptyLabel) return null;
    return <span className="text-slate-400">{emptyLabel}</span>;
  }

  const visible = tags.slice(0, maxVisible);
  const hiddenCount = tags.length - visible.length;

  return (
    <div className={cn("flex flex-wrap items-center gap-1", className)}>
      {visible.map((tag) => (
        <StatusBadge
          key={tag}
          tone="info"
          className={cn("max-w-[8rem] truncate", compact && "px-2 py-0 text-[11px]")}
          title={tag}
        >
          {truncateTag(tag)}
        </StatusBadge>
      ))}
      {hiddenCount > 0 ? (
        compact ? (
          <StatusBadge tone="neutral" className="px-2 py-0 text-[11px]" title={tags.slice(maxVisible).join(", ")}>
            +{hiddenCount}
          </StatusBadge>
        ) : (
          <span className="text-xs text-slate-500" title={tags.slice(maxVisible).join(", ")}>
            +{hiddenCount} more
          </span>
        )
      ) : null}
    </div>
  );
}
