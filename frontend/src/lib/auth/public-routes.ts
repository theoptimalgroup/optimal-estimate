const PUBLIC_ROUTE_PREFIXES = [
  "/assignment",
  "/client/quote",
  "/eworks/calculate",
  "/login",
  "/auth/callback",
] as const;

export function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

/** Routes that must initialize MSAL even when treated as public for auth-context. */
export function isMsalRequiredRoute(pathname: string): boolean {
  if (isMsalAuthCallback(pathname)) {
    return true;
  }
  return pathname === "/login" || pathname.startsWith("/login/");
}

/** Public/token-only routes that must not create or call a PublicClientApplication. */
export function shouldSkipMsalInit(pathname: string): boolean {
  if (isMsalRequiredRoute(pathname)) {
    return false;
  }
  return isPublicRoute(pathname);
}

/** Token-only public routes skip auth-context user loading; MSAL routes still resolve the session. */
export function shouldSkipAuthFetch(pathname: string): boolean {
  if (isMsalRequiredRoute(pathname)) {
    return false;
  }
  return isPublicRoute(pathname);
}

export function isMsalAuthCallback(pathname: string, searchParams?: URLSearchParams | string): boolean {
  if (pathname === "/auth/callback") {
    return true;
  }
  if (pathname !== "/") {
    return false;
  }
  const params =
    typeof searchParams === "string"
      ? new URLSearchParams(searchParams)
      : searchParams ?? null;
  if (!params) {
    return false;
  }
  return params.has("code") || params.has("error") || params.has("state");
}
