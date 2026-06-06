import { describe, expect, it } from "vitest";

import { isMsalAuthCallback, isPublicRoute, shouldSkipAuthFetch, shouldSkipMsalInit } from "@/lib/auth/public-routes";

describe("isPublicRoute", () => {
  it("treats assignment and client quote routes as public", () => {
    expect(isPublicRoute("/assignment/abc-token")).toBe(true);
    expect(isPublicRoute("/client/quote/abc-token")).toBe(true);
    expect(isPublicRoute("/eworks/calculate")).toBe(true);
    expect(isPublicRoute("/eworks/calculate")).toBe(true);
    expect(isPublicRoute("/login")).toBe(true);
    expect(isPublicRoute("/auth/callback")).toBe(true);
  });

  it("keeps staff dashboards protected", () => {
    expect(isPublicRoute("/admin/dashboard")).toBe(false);
    expect(isPublicRoute("/manager/dashboard")).toBe(false);
    expect(isPublicRoute("/estimator/dashboard")).toBe(false);
    expect(isPublicRoute("/engineer/jobs")).toBe(false);
  });
});

describe("shouldSkipMsalInit", () => {
  it("skips MSAL on token-only public routes", () => {
    expect(shouldSkipMsalInit("/assignment/abc-token")).toBe(true);
    expect(shouldSkipMsalInit("/client/quote/abc-token")).toBe(true);
    expect(shouldSkipMsalInit("/eworks/calculate")).toBe(true);
  });

  it("initializes MSAL on login and auth callback routes", () => {
    expect(shouldSkipMsalInit("/login")).toBe(false);
    expect(shouldSkipMsalInit("/auth/callback")).toBe(false);
    expect(shouldSkipMsalInit("/", "?code=abc&state=xyz")).toBe(false);
  });

  it("initializes MSAL on protected staff routes", () => {
    expect(shouldSkipMsalInit("/admin/dashboard")).toBe(false);
    expect(shouldSkipMsalInit("/manager/dashboard")).toBe(false);
  });
});

describe("shouldSkipAuthFetch", () => {
  it("skips auth fetch on token-only public routes", () => {
    expect(shouldSkipAuthFetch("/assignment/abc-token")).toBe(true);
    expect(shouldSkipAuthFetch("/client/quote/abc-token")).toBe(true);
    expect(shouldSkipAuthFetch("/eworks/calculate")).toBe(true);
  });

  it("loads auth on login and MSAL callback routes", () => {
    expect(shouldSkipAuthFetch("/login")).toBe(false);
    expect(shouldSkipAuthFetch("/auth/callback")).toBe(false);
    expect(shouldSkipAuthFetch("/")).toBe(false);
  });

  it("loads auth on protected staff routes", () => {
    expect(shouldSkipAuthFetch("/admin/dashboard")).toBe(false);
    expect(shouldSkipAuthFetch("/manager/dashboard")).toBe(false);
  });
});

describe("isMsalAuthCallback", () => {
  it("detects auth callback routes", () => {
    expect(isMsalAuthCallback("/auth/callback")).toBe(true);
    expect(isMsalAuthCallback("/", "?code=abc&state=xyz")).toBe(true);
    expect(isMsalAuthCallback("/assignment/token")).toBe(false);
  });
});
