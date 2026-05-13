import { Link } from "@tanstack/react-router";
import { Shield } from "lucide-react";
import { Card } from "@/components/ui/card";

const TERMS_SECTIONS = [
  {
    title: "Acceptable use",
    body: "You may use PhishGuard only for lawful security analysis, phishing detection, and related administrative tasks. You must not use the platform to probe third-party systems without permission, disrupt service availability, or violate applicable law.",
  },
  {
    title: "Account responsibilities",
    body: "You are responsible for maintaining the confidentiality of your login credentials and for activity performed through your account. You must provide accurate signup information and promptly notify the platform operator if you suspect unauthorized access.",
  },
  {
    title: "Service availability",
    body: "PhishGuard is provided on a best-effort basis and may change as the platform evolves. We may update features, security controls, retention settings, or access rules when needed to protect users and maintain the service.",
  },
  {
    title: "Suspension and termination",
    body: "We may suspend or remove accounts that violate these terms, threaten platform security, or remain inactive for an extended period. When an account is removed, related records may also be deleted according to the platform retention rules.",
  },
];

export function TermsPage() {
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
          <p className="text-sm font-medium text-primary">Terms of Service</p>
          <h1 className="text-3xl font-bold tracking-tight">Rules for using PhishGuard</h1>
          <p className="max-w-3xl text-sm text-muted-foreground sm:text-base">
            These terms define how the platform may be used, the responsibilities of account
            holders, and how access may be limited to protect the service and its users.
          </p>
        </div>

        <div className="mt-10 space-y-5">
          {TERMS_SECTIONS.map((section) => (
            <Card key={section.title} className="border-border/60 bg-card/70 p-6 shadow-card">
              <h2 className="text-lg font-semibold">{section.title}</h2>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">{section.body}</p>
            </Card>
          ))}
        </div>

        <div className="mt-10 flex flex-wrap gap-3 text-sm">
          <Link to="/privacy" className="font-medium text-primary hover:underline">
            Read the Privacy Policy
          </Link>
          <Link to="/signup" className="font-medium text-primary hover:underline">
            Back to signup
          </Link>
        </div>
      </div>
    </div>
  );
}
