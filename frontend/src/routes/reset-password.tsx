import { createFileRoute } from "@tanstack/react-router";
import { ResetPasswordPage } from "@/pages/ResetPasswordPage";

export const Route = createFileRoute("/reset-password")({
  head: () => ({ meta: [{ title: "Reset password — PhishGuard" }] }),
  component: ResetPasswordPage,
});
