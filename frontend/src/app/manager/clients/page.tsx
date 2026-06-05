"use client";

import { ComingSoonPage } from "@/components/layout/coming-soon-page";
import { useCurrentUser } from "@/lib/auth/auth-context";

export default function ManagerClientsPage() {
  const { role } = useCurrentUser();
  const isAdmin = role === "admin";

  return (
    <ComingSoonPage
      testId="manager-clients-placeholder"
      title="Manager Clients"
      message="Client-level insights for managers will appear here."
      primaryAction={{ label: "Go to Reports", href: "/manager/reports", testId: "manager-clients-go-reports" }}
      secondaryAction={
        isAdmin
          ? { label: "Manage Clients", href: "/admin/clients", testId: "manager-clients-manage-clients" }
          : undefined
      }
      workflowNote="Use Reports to review quote performance by client until manager client views are available."
    />
  );
}
