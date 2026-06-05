"use client";

import Link from "next/link";
import { BarChart3, ClipboardCheck, FileText } from "lucide-react";

import { PageHeader, SectionCard } from "@/components/ui";

const quickLinks = [
  {
    href: "/manager/review",
    label: "Review quotes",
    description: "Approve, reopen, and manage submitted estimates.",
    icon: ClipboardCheck,
  },
  {
    href: "/manager/reports",
    label: "Reports",
    description: "KPIs, trends, and breakdowns by client and trade.",
    icon: BarChart3,
  },
  {
    href: "/manager/clients",
    label: "Clients",
    description: "View client records linked to quotes.",
    icon: FileText,
  },
];

export default function ManagerDashboardPage() {
  return (
    <div className="space-y-6" data-testid="manager-dashboard-page">
      <PageHeader
        title="Manager Dashboard"
        description="Track pending approvals, team workload, and quote pipeline status."
      />

      <div className="grid gap-4 md:grid-cols-3">
        {quickLinks.map((link) => {
          const Icon = link.icon;
          return (
            <Link key={link.href} href={link.href} className="group block">
              <SectionCard className="h-full transition-shadow hover:shadow-md">
                <div className="flex items-start gap-4">
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600 group-hover:bg-blue-100">
                    <Icon className="size-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-semibold text-slate-900">{link.label}</h2>
                    <p className="mt-1 text-sm text-slate-600">{link.description}</p>
                  </div>
                </div>
              </SectionCard>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
