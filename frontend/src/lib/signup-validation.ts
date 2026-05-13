import { getPasswordValidationError } from "@/lib/password-validation";

export function getSignupValidationError(email: string, password: string, confirmPassword: string) {
  if (!email) {
    return { field: "email", message: "Email is required." } as const;
  }

  return getPasswordValidationError(password, confirmPassword);
}
