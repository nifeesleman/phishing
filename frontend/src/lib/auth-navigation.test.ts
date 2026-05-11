import { describe, expect, it } from "vitest";
import {
  getAuthPagePath,
  getDefaultAuthenticatedPath,
  getRequestedRedirectTarget,
  getSafeRedirectTarget,
} from "@/lib/auth-navigation";

describe("auth-navigation", () => {
  it("returns the expected default path", () => {
    expect(getDefaultAuthenticatedPath(true)).toBe("/admin");
    expect(getDefaultAuthenticatedPath(false)).toBe("/dashboard");
  });

  it("only accepts safe redirect targets", () => {
    window.history.replaceState({}, "", "/login?redirect=/admin");
    expect(getRequestedRedirectTarget()).toBe("/admin");
    expect(getSafeRedirectTarget()).toBe("/admin");

    window.history.replaceState({}, "", "/login?redirect=https://example.com");
    expect(getRequestedRedirectTarget()).toBeNull();
    expect(getSafeRedirectTarget()).toBe("/dashboard");
  });

  it("preserves safe redirects when linking between auth pages", () => {
    expect(getAuthPagePath("/signup", "/history")).toBe("/signup?redirect=%2Fhistory");
    expect(getAuthPagePath("/login", null)).toBe("/login");
  });
});
