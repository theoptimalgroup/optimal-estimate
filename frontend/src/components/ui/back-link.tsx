import Link from "next/link";
import type { MouseEventHandler } from "react";

import { cn } from "@/lib/utils";

type BackLinkProps = {
  href: string;
  label: string;
  className?: string;
  onClick?: MouseEventHandler<HTMLAnchorElement>;
  "data-testid"?: string;
};

export function BackLink({
  href,
  label,
  className,
  onClick,
  "data-testid": testId = "back-link",
}: BackLinkProps) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className={cn(
        "mb-4 inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
        className,
      )}
      data-testid={testId}
    >
      ← {label}
    </Link>
  );
}
