import { createFileRoute } from "@tanstack/react-router";
import { TermsPage } from "@/pages/TermsPage";

export const Route = createFileRoute("/terms")({
  head: () => ({ meta: [{ title: "Terms of Service — PhishGuard" }] }),
  component: TermsPage,
});
