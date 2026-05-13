import { describe, expect, it } from "vitest";
import { getPasswordValidationError } from "@/lib/password-validation";

describe("password-validation", () => {
  it("requires a minimum password length", () => {
    expect(getPasswordValidationError("12345", "12345")).toEqual({
      field: "password",
      message: "Password must be at least 6 characters.",
    });
  });

  it("requires the confirm password field", () => {
    expect(getPasswordValidationError("123456", "")).toEqual({
      field: "confirmPassword",
      message: "Please confirm your password.",
    });
  });

  it("rejects mismatched passwords", () => {
    expect(getPasswordValidationError("123456", "654321")).toEqual({
      field: "confirmPassword",
      message: "Passwords do not match.",
    });
  });

  it("accepts a valid password pair", () => {
    expect(getPasswordValidationError("123456", "123456")).toBeNull();
  });
});
