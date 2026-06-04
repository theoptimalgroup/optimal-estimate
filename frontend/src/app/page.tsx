"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useCurrentUser } from "@/lib/auth/auth-context";
import { getDashboardForRole } from "@/lib/auth/dashboard-routes";

function isMsalAuthCallback(searchParams: URLSearchParams): boolean {
  return searchParams.has("code") || searchParams.has("error") || searchParams.has("state");
}

function HomePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isLoading, isAuthenticated } = useCurrentUser();

  const authCallback = isMsalAuthCallback(searchParams);

  useEffect(() => {
    if (authCallback) {
      return;
    }
    router.replace("/eworks/calculate");
  }, [authCallback, router]);

  useEffect(() => {
    if (!authCallback || isLoading || !isAuthenticated || !user) {
      return;
    }
    const dashboard = getDashboardForRole(user.role);
    if (dashboard) {
      router.replace(dashboard);
    }
  }, [authCallback, isLoading, isAuthenticated, user, router]);

  if (authCallback) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50">
        <p className="text-sm text-gray-600">Completing sign-in…</p>
      </main>
    );
  }

  return null;
}

export default function HomePage() {
  return (
    <Suspense fallback={null}>
      <HomePageContent />
    </Suspense>
  );
}
