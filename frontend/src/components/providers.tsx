"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode, useState } from "react";

import { MsalProviderWrapper } from "@/components/auth/msal-provider-wrapper";
import { AuthProvider } from "@/lib/auth/auth-context";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(() => new QueryClient());
  return (
    <MsalProviderWrapper>
      <AuthProvider>
        <QueryClientProvider client={client}>{children}</QueryClientProvider>
      </AuthProvider>
    </MsalProviderWrapper>
  );
}
