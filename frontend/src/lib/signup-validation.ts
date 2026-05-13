import { getPasswordValidationError } from "@/lib/password-validation";

export function getSignupValidationError(
  email: string,
  password: string,
  confirmPassword: string,
  hasAcceptedLegal: boolean,
) {
  if (!email) {
    return { field: "email", message: "Email is required." } as const;
  }

  const passwordValidationError = getPasswordValidationError(password, confirmPassword);
  if (passwordValidationError) {
    return passwordValidationError;
  }

  if (!hasAcceptedLegal) {
    return {
      field: "consent",
      message: "You must agree to the Terms of Service and Privacy Policy.",
    } as const;
  }

  return null;
}
