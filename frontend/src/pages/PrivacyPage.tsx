import { Link } from "@tanstack/react-router";
import { Shield } from "lucide-react";
import { Card } from "@/components/ui/card";

const PRIVACY_SECTIONS = [
  {
    title: "Information we collect",
    body: "We collect the account details you provide during signup, including your email address and authentication metadata. We also store phishing scan activity, timestamps, and basic platform telemetry needed to keep the service reliable and secure.",
  },
  {
    title: "How we use your data",
    body: "Your information is used to authenticate your account, return scan history, operate the phishing-detection service, and monitor abuse or suspicious activity. We process this data to improve platform reliability, investigate incidents, and support administrators who manage the service.",
  },
  {
    title: "Retention and deletion",
    body: "We retain account and scan records only for as long as they are needed to operate the platform. Inactive non-admin accounts may be removed automatically after prolonged inactivity, and related profile and scan records are deleted with the account.",
  },
  {
    title: "Security and access",
    body: "PhishGuard uses authenticated access controls and role-based administration to protect platform data. Only authorized administrators can access aggregated platform analytics, and sensitive account operations require authenticated sessions.",
  },
];

export function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-4xl px-6 py-12">
        <Link to="/" className="inline-flex items-center gap-2 font-semibold">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-primary shadow-glow">
            <Shield className="h-4 w-4 text-primary-foreground" />
          </div>
          PhishGuard
        </Link>

        <div className="mt-8 space-y-3">
          <p className="text-sm font-medium text-primary">Privacy Policy</p>
          <h1 className="text-3xl font-bold tracking-tight">How PhishGuard handles your data</h1>
          <p className="max-w-3xl text-sm text-muted-foreground sm:text-base">
            This policy explains what account and scan information we collect, why we use it, and
            how we protect it while operating the service in a production-style environment.
          </p>
        </div>

        <div className="mt-10 space-y-5">
          {PRIVACY_SECTIONS.map((section) => (
            <Card key={section.title} className="border-border/60 bg-card/70 p-6 shadow-card">
              <h2 className="text-lg font-semibold">{section.title}</h2>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">{section.body}</p>
            </Card>
          ))}
        </div>

        <div className="mt-10 flex flex-wrap gap-3 text-sm">
          <Link to="/terms" className="font-medium text-primary hover:underline">
            Read the Terms of Service
          </Link>
          <Link to="/signup" className="font-medium text-primary hover:underline">
            Back to signup
          </Link>
        </div>
      </div>
    </div>
  );
}
