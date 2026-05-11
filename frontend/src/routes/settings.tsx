import { createFileRoute } from "@tanstack/react-router";
import { SettingsPage } from "@/pages/SettingsPage";

export const Route = createFileRoute("/settings")({
  head: () => ({ meta: [{ title: "Settings — PhishGuard" }] }),
  component: SettingsPage,
});
