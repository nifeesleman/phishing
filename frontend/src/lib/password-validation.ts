export function getPasswordValidationError(password: string, confirmPassword: string) {
  if (password.length < 6) {
    return { field: "password", message: "Password must be at least 6 characters." } as const;
  }

  if (!confirmPassword) {
    return { field: "confirmPassword", message: "Please confirm your password." } as const;
  }

  if (password !== confirmPassword) {
    return { field: "confirmPassword", message: "Passwords do not match." } as const;
  }

  return null;
}
