"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { getCurrentUser } from "@/lib/auth/auth-api";
import { isAzureAuth, isAzureAuthRequested } from "@/lib/auth/auth-config";
import { isAzureConfigured } from "@/lib/auth/msal-config";
import { getAccessToken, onMsalReady } from "@/lib/auth/token-provider";
import type { CurrentUser, UserRole } from "@/lib/auth/types";

type AuthContextValue = {
  user: CurrentUser | null;
  role: UserRole | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  refetchUser: () => Promise<void>;
  hasRole: (...roles: UserRole[]) => boolean;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetchUser = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (isAzureAuth()) {
        const token = await getAccessToken();
        if (!token) {
          setUser(null);
          setError(null);
          return;
        }
      }
      const current = await getCurrentUser();
      setUser(current);
    } catch (err) {
      setUser(null);
      setError(err instanceof Error ? err.message : "Failed to load current user");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAzureAuthRequested()) {
      if (!isAzureConfigured()) {
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      const unsubscribe = onMsalReady(({ hasAccount, hasAccessToken }) => {
        if (!hasAccount || !hasAccessToken) {
          setUser(null);
          setError(null);
          setIsLoading(false);
          return;
        }
        void refetchUser();
      });
      return unsubscribe;
    }

    void refetchUser();
  }, [refetchUser]);

  const hasRole = useCallback(
    (...roles: UserRole[]) => {
      if (!user?.is_active) return false;
      return roles.includes(user.role);
    },
    [user],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      role: user?.role ?? null,
      isLoading,
      isAuthenticated: Boolean(user?.is_active),
      error,
      refetchUser,
      hasRole,
    }),
    [user, isLoading, error, refetchUser, hasRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useCurrentUser(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useCurrentUser must be used within an AuthProvider");
  }
  return context;
}
