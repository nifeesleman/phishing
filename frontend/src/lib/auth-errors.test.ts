import { describe, expect, it } from "vitest";
import {
  getCurrentPasswordErrorMessage,
  getLoginErrorMessage,
  getPasswordUpdateErrorMessage,
  getSignupErrorMessage,
} from "@/lib/auth-errors";

describe("auth-errors", () => {
  it("maps invalid login credentials to a clear message", () => {
    expect(getLoginErrorMessage({ message: "Invalid login credentials" })).toBe(
      "Incorrect email or password.",
    );
  });

  it("maps unconfirmed email errors to a clear message", () => {
    expect(getLoginErrorMessage({ message: "Email not confirmed" })).toBe(
      "Please confirm your email before signing in.",
    );
  });

  it("maps invalid current password errors to a clear message", () => {
    expect(getCurrentPasswordErrorMessage({ message: "Invalid login credentials" })).toBe(
      "Current password is incorrect.",
    );
  });

  it("maps duplicate signup errors to a clear message", () => {
    expect(getSignupErrorMessage({ message: "User already registered" })).toBe(
      "An account with this email already exists.",
    );
  });

  it("maps password update errors to a clear message", () => {
    expect(
      getPasswordUpdateErrorMessage({
        message: "New password should be different from the old password.",
      }),
    ).toBe("Choose a different password than your current one.");
  });
});
