import { afterEach, describe, expect, it, vi } from "vitest";
import {
  buildCommittedTranscriptBuffer,
  getElevenLabsToken,
  getWebSocketCloseUserMessage,
  isBadGenericFragment,
  isNormalWebSocketClose,
  isTranscriptEmptyOrFiller,
  parseWebSocketCloseCode,
  selectFinalTranscript,
} from "@/lib/voice-api";

vi.mock("@/lib/api", () => ({
  getApiUrl: () => "http://localhost:8000",
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      message: string,
    ) {
      super(message);
    }
  },
  extractApiErrorMessage: (_payload: unknown, fallback: string) => fallback,
}));

vi.mock("@/lib/auth/public-routes", () => ({
  shouldSkipMsalInit: () => true,
}));

vi.mock("@/lib/auth/token-provider", () => ({
  getAccessToken: vi.fn().mockResolvedValue(null),
}));

describe("getElevenLabsToken", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns token from wrapped API response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        statusText: "OK",
        text: async () =>
          JSON.stringify({
            success: true,
            data: { token: "sutkn_test" },
            meta: {},
          }),
      }),
    );

    await expect(getElevenLabsToken()).resolves.toEqual({ token: "sutkn_test" });
  });

  it("returns token from top-level response shape", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        statusText: "OK",
        text: async () => JSON.stringify({ token: "sutkn_test" }),
      }),
    );

    await expect(getElevenLabsToken()).resolves.toEqual({ token: "sutkn_test" });
  });
});

describe("voice WebSocket close helpers", () => {
  it("treats code 1000 as a normal close", () => {
    const error = new Error('WebSocket closed unexpectedly: 1000 - User ended session');
    expect(parseWebSocketCloseCode(error)).toBe(1000);
    expect(isNormalWebSocketClose(error)).toBe(true);
    expect(getWebSocketCloseUserMessage(error)).toBeNull();
  });

  it("treats code 1005 as a normal close", () => {
    const error = new Error("WebSocket closed unexpectedly: 1005 - No reason provided");
    expect(isNormalWebSocketClose(error)).toBe(true);
    expect(getWebSocketCloseUserMessage(error)).toBeNull();
  });

  it("returns a user-friendly message for code 1006", () => {
    const error = new Error("WebSocket closed unexpectedly: 1006 - No reason provided");
    expect(isNormalWebSocketClose(error)).toBe(false);
    expect(getWebSocketCloseUserMessage(error)).toBe(
      "Voice connection dropped. Please try recording again.",
    );
  });
});

describe("voice transcript selection", () => {
  it("builds committed transcript buffer from segments", () => {
    expect(
      buildCommittedTranscriptBuffer([
        { text: "Install panels" },
        { text: "  on roof  " },
        { text: "" },
      ]),
    ).toBe("Install panels on roof");
  });

  it("detects bad generic fragments case-insensitively", () => {
    expect(isBadGenericFragment("Hello.")).toBe(true);
    expect(isBadGenericFragment("A room.")).toBe(true);
    expect(isBadGenericFragment("A room. Hello.")).toBe(true);
    expect(isBadGenericFragment("Install ten by ten meter panels")).toBe(false);
  });

  it("uses exact whole-string match for bad fragments — 'a room' must not match 'There is a room.'", () => {
    expect(isBadGenericFragment("a room")).toBe(true);
    expect(isBadGenericFragment("A room.")).toBe(true);
    expect(isBadGenericFragment("There is a room.")).toBe(false);
    expect(isBadGenericFragment("There is a room")).toBe(false);
  });

  it("uses partial transcript when committed text is empty", () => {
    expect(selectFinalTranscript("", "Install solar panels on the north roof")).toBe(
      "Install solar panels on the north roof",
    );
  });

  it("uses partial transcript when committed text is short and partial is longer", () => {
    expect(selectFinalTranscript("Hello.", "Install solar panels on the north roof")).toBe(
      "Install solar panels on the north roof",
    );
  });

  it("uses partial transcript when committed text is a bad generic fragment", () => {
    expect(
      selectFinalTranscript(
        "A room. Hello.",
        "The room is ten by ten meters with south-facing windows",
      ),
    ).toBe("The room is ten by ten meters with south-facing windows");
  });

  it("uses partial transcript when it has more meaningful words", () => {
    expect(
      selectFinalTranscript(
        "Testing complete",
        "Replace inverter and run cable ten meters to switchboard",
      ),
    ).toBe("Replace inverter and run cable ten meters to switchboard");
  });

  it("keeps committed transcript when it is longer and more meaningful", () => {
    const committed =
      "Replace the inverter and run cable ten meters from the switchboard to the roof";
    expect(selectFinalTranscript(committed, "Replace inverter")).toBe(committed);
  });

  it("treats empty and filler-only transcripts as unusable", () => {
    expect(isTranscriptEmptyOrFiller("")).toBe(true);
    expect(isTranscriptEmptyOrFiller("   ")).toBe(true);
    expect(isTranscriptEmptyOrFiller("hello")).toBe(true);
    expect(isTranscriptEmptyOrFiller("um uh ah")).toBe(true);
    expect(isTranscriptEmptyOrFiller("Install ten by ten meter panels")).toBe(false);
  });

  it("accepts short but meaningful sentences as valid transcripts", () => {
    expect(isTranscriptEmptyOrFiller("There is a room.")).toBe(false);
    expect(isTranscriptEmptyOrFiller("There is a room")).toBe(false);
    expect(isTranscriptEmptyOrFiller("Paint the ceiling.")).toBe(false);
    expect(isTranscriptEmptyOrFiller("Fix the boiler.")).toBe(false);
  });

  it("selects partial over a bad committed fragment even when partial is 'There is a room.'", () => {
    expect(
      selectFinalTranscript("A room. Hello.", "There is a room."),
    ).toBe("There is a room.");
  });

  it("keeps 'There is a room.' as committed when partial is absent", () => {
    expect(selectFinalTranscript("There is a room.", "")).toBe("There is a room.");
  });
});
