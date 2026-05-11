type AuthErrorLike = {
  message?: string | null;
};

export function getLoginErrorMessage(error: AuthErrorLike | null | undefined) {
  const message = error?.message?.trim();
  const normalizedMessage = message?.toLowerCase() ?? "";

  if (
    normalizedMessage.includes("invalid login credentials") ||
    normalizedMessage.includes("invalid credentials")
  ) {
    return "Incorrect email or password.";
  }

  if (normalizedMessage.includes("email not confirmed")) {
    return "Please confirm your email before signing in.";
  }

  if (normalizedMessage.includes("invalid email")) {
    return "Please enter a valid email address.";
  }

  return message || "Sign in failed. Please try again.";
}

export function getCurrentPasswordErrorMessage(error: AuthErrorLike | null | undefined) {
  const loginMessage = getLoginErrorMessage(error);
  return loginMessage === "Incorrect email or password."
    ? "Current password is incorrect."
    : loginMessage;
}

export function getSignupErrorMessage(error: AuthErrorLike | null | undefined) {
  const message = error?.message?.trim();
  const normalizedMessage = message?.toLowerCase() ?? "";

  if (normalizedMessage.includes("user already registered")) {
    return "An account with this email already exists.";
  }

  if (normalizedMessage.includes("password should be at least 6 characters")) {
    return "Password must be at least 6 characters.";
  }

  if (normalizedMessage.includes("invalid email")) {
    return "Please enter a valid email address.";
  }

  return message || "Sign up failed. Please try again.";
}

export function getPasswordUpdateErrorMessage(error: AuthErrorLike | null | undefined) {
  const message = error?.message?.trim();
  const normalizedMessage = message?.toLowerCase() ?? "";

  if (
    normalizedMessage.includes("password should be at least 6 characters") ||
    normalizedMessage.includes("password must be at least 6 characters")
  ) {
    return "Password must be at least 6 characters.";
  }

  if (
    normalizedMessage.includes("new password should be different") ||
    normalizedMessage.includes("same password")
  ) {
    return "Choose a different password than your current one.";
  }

  return message || "Password update failed. Please try again.";
}
