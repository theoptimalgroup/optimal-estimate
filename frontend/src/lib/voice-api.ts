import { apiFetch, ApiError, extractApiErrorMessage, getApiUrl } from "@/lib/api";
import { shouldSkipMsalInit } from "@/lib/auth/public-routes";
import { getAccessToken } from "@/lib/auth/token-provider";

export type VoiceCleanupContext =
  | "scope_of_work"
  | "internal_notes"
  | "engineer_findings"
  | "client_description"
  | "manager_review_notes";

const NORMAL_WEBSOCKET_CLOSE_CODES = new Set([1000, 1005]);

export function parseWebSocketCloseCode(error: Error | Event): number | null {
  if (!(error instanceof Error)) {
    return null;
  }

  const match = error.message.match(/WebSocket closed unexpectedly:\s*(\d+)/);
  return match ? Number(match[1]) : null;
}

export function isNormalWebSocketClose(error: Error | Event): boolean {
  const closeCode = parseWebSocketCloseCode(error);
  return closeCode !== null && NORMAL_WEBSOCKET_CLOSE_CODES.has(closeCode);
}

export function getWebSocketCloseUserMessage(error: Error | Event): string | null {
  const closeCode = parseWebSocketCloseCode(error);
  if (closeCode === null) {
    return null;
  }

  if (NORMAL_WEBSOCKET_CLOSE_CODES.has(closeCode)) {
    return null;
  }

  if (closeCode === 1006) {
    return "Voice connection dropped. Please try recording again.";
  }

  return "Voice connection dropped. Please try recording again.";
}

export type ElevenLabsTokenResponse = {
  token: string;
};

function extractElevenLabsToken(payload: object): string | null {
  const topLevelToken = (payload as { token?: unknown }).token;
  if (typeof topLevelToken === "string" && topLevelToken.trim()) {
    return topLevelToken;
  }

  const data = (payload as { data?: unknown }).data;
  if (data && typeof data === "object") {
    const nestedToken = (data as { token?: unknown }).token;
    if (typeof nestedToken === "string" && nestedToken.trim()) {
      return nestedToken;
    }
  }

  return null;
}

export async function getElevenLabsToken(): Promise<ElevenLabsTokenResponse> {
  console.info("[voice] ElevenLabs token request started");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const skipAuth =
    typeof window !== "undefined" && shouldSkipMsalInit(window.location.pathname);
  const authToken = skipAuth ? null : await getAccessToken();
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  let response: Response;
  try {
    response = await fetch(`${getApiUrl()}/api/v1/voice/elevenlabs-token`, { headers });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Network request failed";
    console.error("[voice] ElevenLabs token request failed response body", message);
    throw new ApiError(0, message);
  }

  console.info("[voice] ElevenLabs token request status code", response.status);

  const rawBody = await response.text();
  let payload: unknown = null;
  if (rawBody) {
    try {
      payload = JSON.parse(rawBody);
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    console.error("[voice] ElevenLabs token request failed response body", rawBody || response.statusText);
    const fallback = rawBody?.trim() || response.statusText || "Request failed";
    throw new ApiError(response.status, extractApiErrorMessage(payload, fallback));
  }

  if (!payload || typeof payload !== "object") {
    throw new ApiError(response.status, "Empty response from server");
  }

  const token = extractElevenLabsToken(payload);
  if (!token) {
    throw new ApiError(response.status, "Token missing from server response");
  }

  return { token };
}

export async function cleanVoiceText(text: string, context: VoiceCleanupContext): Promise<string> {
  const response = await apiFetch<{ text: string }>("/api/v1/voice/clean-text", {
    method: "POST",
    body: JSON.stringify({ text, context }),
  });
  return response.data.text;
}

const BAD_GENERIC_FRAGMENTS = new Set(["hello", "a room", "okay", "yes", "test", "testing"]);

const FILLER_WORDS = new Set(["um", "uh", "ah", "oh", "hmm", "hm", "er", "like"]);

export function buildCommittedTranscriptBuffer(segments: Array<{ text: string }>): string {
  return segments
    .map((segment) => segment.text.trim())
    .filter(Boolean)
    .join(" ")
    .trim();
}

function normalizeFragment(text: string): string {
  return text.trim().toLowerCase().replace(/[.!?,;]+$/, "");
}

export function isBadGenericFragment(text: string): boolean {
  const normalized = normalizeFragment(text);
  if (BAD_GENERIC_FRAGMENTS.has(normalized)) {
    return true;
  }

  const phrases = text
    .split(/[.!?,;]+/)
    .map((phrase) => normalizeFragment(phrase))
    .filter(Boolean);

  return phrases.length > 0 && phrases.every((phrase) => BAD_GENERIC_FRAGMENTS.has(phrase));
}

export function countMeaningfulWords(text: string): number {
  return text
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .filter((word) => {
      const normalized = word.toLowerCase().replace(/[^\w]/g, "");
      return normalized.length > 0 && !FILLER_WORDS.has(normalized);
    }).length;
}

export function selectFinalTranscript(committedText: string, latestPartialTranscript: string): string {
  const committed = committedText.trim();
  const partial = latestPartialTranscript.trim();

  if (!committed) {
    return partial;
  }

  if (committed.length < 15 && partial.length > committed.length) {
    return partial;
  }

  if (isBadGenericFragment(committed)) {
    return partial || committed;
  }

  if (partial && countMeaningfulWords(partial) > countMeaningfulWords(committed)) {
    return partial;
  }

  return committed;
}

export function isTranscriptEmptyOrFiller(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) {
    return true;
  }

  if (isBadGenericFragment(trimmed)) {
    return true;
  }

  return countMeaningfulWords(trimmed) === 0;
}
