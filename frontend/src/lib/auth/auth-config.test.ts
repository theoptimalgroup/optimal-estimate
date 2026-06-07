import { describe, expect, it } from "vitest";

import { getAuthProvider, isAzureAuthRequested, isDevAuth } from "@/lib/auth/auth-config";

describe("auth-config", () => {
  it("defaults to dev provider in local/test builds", () => {
    expect(getAuthProvider()).toBe("dev");
    expect(isDevAuth()).toBe(true);
    expect(isAzureAuthRequested()).toBe(false);
  });
});
