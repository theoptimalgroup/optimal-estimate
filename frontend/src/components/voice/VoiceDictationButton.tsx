"use client";

import { memo, useCallback, useEffect, useId, useRef, useState } from "react";
import { CommitStrategy, RealtimeEvents, useScribe } from "@elevenlabs/react";
import { EworksButton } from "@/components/eworks-ui";
import {
  cleanVoiceText,
  getElevenLabsToken,
  getWebSocketCloseUserMessage,
  isNormalWebSocketClose,
  isTranscriptEmptyOrFiller,
  selectFinalTranscript,
  type VoiceCleanupContext,
} from "@/lib/voice-api";

export type VoiceDictationButtonProps = {
  context: VoiceCleanupContext;
  onCleanText: (text: string) => void;
  mode?: "append" | "replace";
  disabled?: boolean;
  label?: string;
  fieldLabel?: string;
  workIndex?: number;
};

type VoiceDictationStatus = "idle" | "connecting" | "recording" | "cleaning" | "done" | "error";

let voiceMountCount = 0;
let voiceUnmountCount = 0;

function noSpeechMessage(fieldLabel?: string): string {
  return fieldLabel
    ? `No speech was captured for ${fieldLabel}. Please try again.`
    : "No speech was captured. Please try again.";
}

function statusLabel(status: VoiceDictationStatus, fieldLabel?: string): string {
  switch (status) {
    case "connecting":
      return "Connecting…";
    case "recording":
      return fieldLabel ? `Recording ${fieldLabel}...` : "Recording...";
    case "cleaning":
      return "Cleaning…";
    case "done":
      return "Done";
    case "error":
      return "Error";
    default:
      return "";
  }
}

function VoiceDictationButtonInner({
  context,
  onCleanText,
  mode = "append",
  disabled = false,
  label,
  fieldLabel,
  workIndex,
}: VoiceDictationButtonProps) {
  const instanceId = useId();
  const [status, setStatus] = useState<VoiceDictationStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [finalTranscriptSentToCleanup, setFinalTranscriptSentToCleanup] = useState<string | null>(null);
  const [showDebug, setShowDebug] = useState(false);
  const [latestPartialTranscript, setLatestPartialTranscript] = useState("");
  const [committedText, setCommittedText] = useState("");
  const committedBufferRef = useRef<string[]>([]);
  const latestPartialTranscriptRef = useRef("");
  const statusRef = useRef<VoiceDictationStatus>("idle");
  const intentionalDisconnectRef = useRef(false);
  const mountCountRef = useRef(0);

  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  const syncCommittedDebug = useCallback(() => {
    const joined = committedBufferRef.current.join(" ").trim();
    setCommittedText(joined);
  }, []);

  const handleUnexpectedDisconnect = useCallback(() => {
    if (intentionalDisconnectRef.current) {
      intentionalDisconnectRef.current = false;
      return;
    }

    if (statusRef.current !== "recording") {
      return;
    }

    const hasCommitted = committedBufferRef.current.length > 0;
    const hasPartial = latestPartialTranscriptRef.current.trim().length > 0;
    if (!hasCommitted && !hasPartial) {
      setError(noSpeechMessage(fieldLabel));
      setStatus("error");
    }
  }, [fieldLabel]);

  const handleScribeError = useCallback((err: unknown) => {
    if (err instanceof Error) {
      if (isNormalWebSocketClose(err)) {
        return;
      }

      const closeMessage = getWebSocketCloseUserMessage(err);
      if (closeMessage) {
        console.error("[voice] Scribe WebSocket closed abnormally:", err);
        setError(closeMessage);
        setStatus("error");
        return;
      }

      console.error("[voice] Scribe error:", err);
      setError(err.message || "Voice dictation failed");
      setStatus("error");
      return;
    }

    if (err && typeof err === "object" && "error" in err && typeof (err as { error: unknown }).error === "string") {
      const message = (err as { error: string }).error;
      console.error("[voice] Scribe error:", message);
      setError(message);
      setStatus("error");
      return;
    }

    console.error("[voice] Scribe error:", err);
    setError("Voice dictation failed");
    setStatus("error");
  }, []);

  const scribe = useScribe({
    modelId: "scribe_v2_realtime",
    commitStrategy: CommitStrategy.VAD,
    languageCode: "en",
    onCommittedTranscript: (data) => {
      console.info("[voice] committed transcript received", {
        instanceId,
        fieldLabel,
        workIndex,
        text: data.text,
      });
      committedBufferRef.current.push(data.text);
      latestPartialTranscriptRef.current = "";
      setLatestPartialTranscript("");
      syncCommittedDebug();
    },
    onPartialTranscript: (data) => {
      const text = data.text?.trim() ?? "";
      latestPartialTranscriptRef.current = text;
      setLatestPartialTranscript(text);
      console.info("[voice] partial transcript received", {
        instanceId,
        fieldLabel,
        workIndex,
        text,
      });
    },
    onDisconnect: () => {
      handleUnexpectedDisconnect();
    },
  });

  const scribeRef = useRef(scribe);
  scribeRef.current = scribe;

  useEffect(() => {
    mountCountRef.current += 1;
    voiceMountCount += 1;
    console.info("[voice] component mounted", {
      instanceId,
      fieldLabel,
      context,
      workIndex,
      mountCount: mountCountRef.current,
      globalMountCount: voiceMountCount,
    });

    return () => {
      voiceUnmountCount += 1;
      console.info("[voice] component unmounted", {
        instanceId,
        fieldLabel,
        context,
        workIndex,
        globalUnmountCount: voiceUnmountCount,
      });
      if (scribeRef.current.isConnected) {
        intentionalDisconnectRef.current = true;
        scribeRef.current.disconnect();
      }
    };
  }, [context, fieldLabel, instanceId, workIndex]);

  const resetSession = useCallback(() => {
    committedBufferRef.current = [];
    latestPartialTranscriptRef.current = "";
    setLatestPartialTranscript("");
    setCommittedText("");
    scribeRef.current.clearTranscripts();
    setFinalTranscriptSentToCleanup(null);
    setError(null);
  }, []);

  const handleStart = useCallback(
    async (event: React.MouseEvent<HTMLButtonElement>) => {
      event.preventDefault();
      event.stopPropagation();

      if (disabled || status === "connecting" || status === "recording" || status === "cleaning") {
        return;
      }

      resetSession();
      setStatus("connecting");

      try {
        console.info("[voice] token fetched", { instanceId, fieldLabel, workIndex, context });
        const tokenResponse = await getElevenLabsToken();
        console.info("[voice] token received", {
          instanceId,
          hasToken: Boolean(tokenResponse.token),
          tokenPrefix: tokenResponse.token?.slice(0, 6),
        });

        if (!tokenResponse.token) {
          setError("Voice token was invalid. Please try again.");
          setStatus("error");
          return;
        }

        console.info("[voice] recording started", { instanceId, fieldLabel, workIndex, context });
        await scribeRef.current.connect({
          token: tokenResponse.token,
          microphone: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });

        const connection = scribeRef.current.getConnection();
        if (connection) {
          connection.on(RealtimeEvents.ERROR, handleScribeError);
        }

        console.info("[voice] scribe connected", { instanceId, fieldLabel, workIndex, context });
        setStatus("recording");
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to start dictation";
        setError(message);
        setStatus("error");
      }
    },
    [context, disabled, fieldLabel, handleScribeError, instanceId, resetSession, status, workIndex],
  );

  const handleStopAndClean = useCallback(
    async (event: React.MouseEvent<HTMLButtonElement>) => {
      event.preventDefault();
      event.stopPropagation();

      if (status !== "recording") {
        return;
      }

      console.info("[voice] stop clicked", { instanceId, fieldLabel, workIndex, context });
      intentionalDisconnectRef.current = true;
      scribeRef.current.disconnect();

      const committed = committedBufferRef.current.join(" ").trim();
      const partial = latestPartialTranscriptRef.current.trim();
      const finalTranscript = selectFinalTranscript(committed, partial);
      console.info("[voice] final transcript selected", {
        instanceId,
        fieldLabel,
        workIndex,
        committed,
        partial,
        finalTranscript,
      });
      setFinalTranscriptSentToCleanup(finalTranscript);

      if (isTranscriptEmptyOrFiller(finalTranscript)) {
        setError(noSpeechMessage(fieldLabel));
        setStatus("error");
        return;
      }

      setStatus("cleaning");
      setError(null);

      try {
        console.info("[voice] clean-text called", {
          instanceId,
          fieldLabel,
          workIndex,
          context,
          textLength: finalTranscript.length,
        });
        const cleaned = await cleanVoiceText(finalTranscript, context);
        console.info("[voice] clean-text success", {
          instanceId,
          fieldLabel,
          workIndex,
          cleanedLength: cleaned.length,
        });
        onCleanText(cleaned);
        setStatus("done");
        window.setTimeout(() => {
          setStatus("idle");
          resetSession();
        }, 1500);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to clean dictated text";
        console.error("[voice] clean-text error", { instanceId, fieldLabel, workIndex, message });
        setError(message);
        setStatus("error");
      }
    },
    [context, fieldLabel, instanceId, onCleanText, resetSession, status, workIndex],
  );

  const handleCancel = useCallback(
    (event: React.MouseEvent<HTMLButtonElement>) => {
      event.preventDefault();
      event.stopPropagation();

      console.info("[voice] cancel clicked", { instanceId, fieldLabel, workIndex, context });
      intentionalDisconnectRef.current = true;
      scribeRef.current.disconnect();
      resetSession();
      setStatus("idle");
    },
    [context, fieldLabel, instanceId, resetSession, workIndex],
  );

  const handleClearDebug = useCallback(
    (event: React.MouseEvent<HTMLButtonElement>) => {
      event.preventDefault();
      event.stopPropagation();
      resetSession();
      setFinalTranscriptSentToCleanup(null);
      setStatus("idle");
    },
    [resetSession],
  );

  const isBusy = status === "connecting" || status === "recording" || status === "cleaning";
  const isRecording = status === "recording";
  const statusText = statusLabel(status, fieldLabel);

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap items-center gap-2">
        {isRecording ? (
          <>
            <EworksButton
              type="button"
              variant="secondary"
              className="min-h-[36px] px-3 text-xs"
              disabled={disabled}
              onClick={(event) => void handleStopAndClean(event)}
              data-testid={`voice-stop-clean-${context}`}
            >
              Stop &amp; Clean
            </EworksButton>
            <EworksButton
              type="button"
              variant="ghost"
              className="min-h-[36px] px-3 text-xs"
              disabled={disabled}
              onClick={handleCancel}
              data-testid={`voice-cancel-${context}`}
            >
              Cancel
            </EworksButton>
          </>
        ) : (
          <EworksButton
            type="button"
            variant="secondary"
            className="min-h-[36px] px-3 text-xs"
            disabled={disabled || isBusy}
            onClick={(event) => void handleStart(event)}
            data-testid={`voice-dictate-${context}`}
          >
            {status === "connecting" ? "Connecting…" : status === "cleaning" ? "Cleaning…" : (label ?? "Dictate")}
          </EworksButton>
        )}
        {process.env.NODE_ENV === "development" && finalTranscriptSentToCleanup ? (
          <button
            type="button"
            className="text-[11px] font-medium text-slate-500 hover:text-slate-700"
            onClick={() => setShowDebug((current) => !current)}
          >
            {showDebug ? "Hide raw" : "Raw"}
          </button>
        ) : null}
        {process.env.NODE_ENV === "development" ? (
          <button
            type="button"
            className="text-[11px] font-medium text-slate-500 hover:text-slate-700"
            onClick={handleClearDebug}
          >
            Clear
          </button>
        ) : null}
      </div>
      {statusText ? (
        <span className="text-[11px] font-medium text-slate-500" data-testid={`voice-status-${context}`}>
          {statusText}
          {mode === "append" ? " · append" : " · replace"}
        </span>
      ) : null}
      {error ? (
        <span className="max-w-xs text-right text-[11px] font-medium text-red-600" data-testid={`voice-error-${context}`}>
          {error}
        </span>
      ) : null}
      {showDebug && finalTranscriptSentToCleanup ? (
        <pre className="max-w-sm whitespace-pre-wrap rounded border border-slate-200 bg-slate-50 p-2 text-left text-[10px] text-slate-700">
          {finalTranscriptSentToCleanup}
        </pre>
      ) : null}
      {process.env.NODE_ENV === "development" ? (
        <div
          className="max-w-sm rounded border border-dashed border-slate-300 bg-slate-50 p-2 text-left text-[10px] text-slate-600"
          data-testid={`voice-debug-panel-${context}`}
        >
          <p className="font-semibold text-slate-700">Voice debug</p>
          <p>instance: {instanceId}</p>
          <p>field: {fieldLabel ?? context}</p>
          <p>work index: {workIndex ?? "—"}</p>
          <p>recording: {String(isRecording)}</p>
          <p>partial: {latestPartialTranscript || "—"}</p>
          <p>committed: {committedText || "—"}</p>
          <p>final sent: {finalTranscriptSentToCleanup ?? "—"}</p>
          <p>mounts: {mountCountRef.current} / global {voiceMountCount}</p>
          <p>unmounts: global {voiceUnmountCount}</p>
        </div>
      ) : null}
    </div>
  );
}

export const VoiceDictationButton = memo(VoiceDictationButtonInner);
