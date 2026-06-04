type AccessTokenGetter = () => Promise<string | null>;

export type MsalReadyPayload = {
  /** MSAL has a cached Microsoft account */
  hasAccount: boolean;
  /** Silent token acquisition succeeded — safe to call /auth/me */
  hasAccessToken: boolean;
};

let accessTokenGetter: AccessTokenGetter | null = null;
const msalReadyListeners = new Set<(payload: MsalReadyPayload) => void>();

export function setAccessTokenGetter(getter: AccessTokenGetter | null): void {
  accessTokenGetter = getter;
}

export function onMsalReady(listener: (payload: MsalReadyPayload) => void): () => void {
  msalReadyListeners.add(listener);
  return () => {
    msalReadyListeners.delete(listener);
  };
}

export function notifyMsalReady(payload: MsalReadyPayload): void {
  for (const listener of msalReadyListeners) {
    listener(payload);
  }
}

export async function getAccessToken(): Promise<string | null> {
  if (!accessTokenGetter) {
    return null;
  }
  return accessTokenGetter();
}

export async function getAuthHeaders(
  extra: Record<string, string> = {},
): Promise<Record<string, string>> {
  const headers: Record<string, string> = { ...extra };
  const token = await getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}
