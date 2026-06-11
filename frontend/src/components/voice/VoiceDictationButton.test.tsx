import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockConnect = vi.fn().mockResolvedValue(undefined);
const mockDisconnect = vi.fn();
const mockClearTranscripts = vi.fn();
const mockGetConnection = vi.fn().mockReturnValue(null);

vi.mock("@elevenlabs/react", () => ({
  CommitStrategy: { VAD: "vad" },
  RealtimeEvents: { ERROR: "error" },
  useScribe: () => ({
    connect: mockConnect,
    disconnect: mockDisconnect,
    clearTranscripts: mockClearTranscripts,
    getConnection: mockGetConnection,
    isConnected: false,
    committedTranscripts: [],
    partialTranscript: "",
  }),
}));

const mockGetElevenLabsToken = vi.fn();

vi.mock("@/lib/voice-api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/voice-api")>();
  return {
    ...original,
    getElevenLabsToken: (...args: Parameters<typeof original.getElevenLabsToken>) =>
      mockGetElevenLabsToken(...args),
  };
});

import { VoiceDictationButton } from "@/components/voice/VoiceDictationButton";

describe("VoiceDictationButton", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    mockConnect.mockClear();
    mockGetElevenLabsToken.mockReset();
    mockGetElevenLabsToken.mockResolvedValue({ token: "sutkn_test" });

    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it("passes token string to scribe.connect, not the full response object", async () => {
    const onCleanText = vi.fn();

    await act(async () => {
      root.render(
        <VoiceDictationButton context="scope_of_work" onCleanText={onCleanText} />,
      );
    });

    const dictateButton = container.querySelector(
      '[data-testid="voice-dictate-scope_of_work"]',
    ) as HTMLButtonElement;

    await act(async () => {
      dictateButton.click();
      await Promise.resolve();
    });

    expect(mockGetElevenLabsToken).toHaveBeenCalledTimes(1);
    expect(mockConnect).toHaveBeenCalledTimes(1);

    const connectArgs = mockConnect.mock.calls[0]?.[0];
    expect(connectArgs).toEqual(
      expect.objectContaining({
        token: "sutkn_test",
        microphone: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      }),
    );
    expect(typeof connectArgs.token).toBe("string");
    expect(connectArgs.token).not.toEqual({ token: "sutkn_test" });
  });
});
