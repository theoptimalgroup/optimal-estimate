import { cn } from "@/lib/utils";

export type PageTabItem<T extends string> = {
  id: T;
  label: string;
};

export function PageTabs<T extends string>({
  tabs,
  activeTab,
  onTabChange,
  testIdPrefix = "tab",
  className,
}: {
  tabs: readonly PageTabItem<T>[];
  activeTab: T;
  onTabChange: (tab: T) => void;
  testIdPrefix?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex gap-1 border-b border-slate-200", className)} role="tablist">
      {tabs.map((tab) => {
        const active = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onTabChange(tab.id)}
            data-testid={`${testIdPrefix}-${tab.id}`}
            className={cn(
              "px-4 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30 focus-visible:ring-offset-2",
              active
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-slate-500 hover:text-slate-700",
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
