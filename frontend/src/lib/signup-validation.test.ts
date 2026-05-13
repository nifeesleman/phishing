import { describe, expect, it } from "vitest";
import { getSignupValidationError } from "@/lib/signup-validation";

describe("signup-validation", () => {
  it("requires a minimum password length", () => {
    expect(getSignupValidationError("user@example.com", "12345", "12345", true)).toEqual({
      field: "password",
      message: "Password must be at least 6 characters.",
    });
  });

  it("requires the confirm password field", () => {
    expect(getSignupValidationError("user@example.com", "123456", "", true)).toEqual({
      field: "confirmPassword",
      message: "Please confirm your password.",
    });
  });

  it("rejects mismatched passwords", () => {
    expect(getSignupValidationError("user@example.com", "123456", "654321", true)).toEqual({
      field: "confirmPassword",
      message: "Passwords do not match.",
    });
  });

  it("requires legal consent", () => {
    expect(getSignupValidationError("user@example.com", "123456", "123456", false)).toEqual({
      field: "consent",
      message: "You must agree to the Terms of Service and Privacy Policy.",
    });
  });
});
