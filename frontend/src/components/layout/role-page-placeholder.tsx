import type { ReactNode } from "react";

import { SectionCard } from "@/components/ui";

type RolePagePlaceholderProps = {
  title: string;
  description: string;
  children?: ReactNode;
};

export function RolePagePlaceholder({ title, description, children }: RolePagePlaceholderProps) {
  return (
    <SectionCard>
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
        <p className="text-sm text-slate-600">{description}</p>
        {children}
      </div>
    </SectionCard>
  );
}
