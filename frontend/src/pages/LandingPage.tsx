import { Link } from "@tanstack/react-router";
import { Shield, Zap, History, ArrowRight, Check, Database, BarChart3 } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { getAuthPagePath } from "@/lib/auth-navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Header } from "@/components/Header";

export function LandingPage() {
  const { user } = useAuth();
  const dashboardDestination = user ? "/dashboard" : getAuthPagePath("/login", "/dashboard");

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <section className="relative overflow-hidden bg-gradient-hero">
        <div className="mx-auto max-w-6xl px-6 py-24 sm:py-32">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border/60 bg-card/40 px-3 py-1 text-xs text-muted-foreground backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-success" />
              Flask ML API + React client
            </div>
            <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
              Detect phishing links before{" "}
              <span className="bg-gradient-primary bg-clip-text text-black">they reach users</span>
            </h1>
            <p className="mt-6 text-lg text-muted-foreground">
              PhishGuard combines a production Flask prediction API, Supabase authentication, and a
              modern React interface to help teams scan URLs, track history, and monitor trends.
            </p>
            <div className="mt-8 flex items-center justify-center gap-3">
              <Button asChild size="lg" className="shadow-glow">
                <Link to="/signup">
                  Start scanning <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link to="/login">I have an account</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-20">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {[
            {
              icon: Zap,
              title: "Fast ML inference",
              text: "URLs are normalized, vectorized, and scored by the backend model with a clean JSON API response.",
            },
            {
              icon: History,
              title: "User scan history",
              text: "Every authenticated scan is stored server-side so users can filter, review, and export past results.",
            },
            {
              icon: BarChart3,
              title: "Admin analytics",
              text: "Administrators can monitor scan volume, high-risk URLs, and platform-wide threat trends.",
            },
          ].map(({ icon: Icon, title, text }) => (
            <Card key={title} className="border-border/60 bg-card/60 p-6 shadow-card">
              <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-primary text-primary-foreground">
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="mb-2 text-lg font-semibold">{title}</h3>
              <p className="text-sm text-muted-foreground">{text}</p>
            </Card>
          ))}
        </div>
      </section>

      <section className="border-t border-border/60 bg-card/30">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight">How the platform works</h2>
            <p className="mt-3 text-muted-foreground">
              Cleanly separated layers keep the system maintainable and production-ready.
            </p>
          </div>
          <div className="mx-auto mt-12 max-w-3xl space-y-4">
            {[
              {
                n: "1",
                t: "Client request",
                d: "The React app sends the URL to the Flask backend over HTTP with the user session token.",
              },
              {
                n: "2",
                t: "Backend prediction",
                d: "The API validates the input, preprocesses the URL, runs the ML model, and stores the result.",
              },
              {
                n: "3",
                t: "Insights and history",
                d: "Users review their history and admins inspect analytics without exposing database or model logic to the browser.",
              },
            ].map((step) => (
              <Card key={step.n} className="flex items-start gap-4 border-border/60 bg-card/60 p-5">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-primary font-semibold text-primary-foreground">
                  {step.n}
                </div>
                <div>
                  <h3 className="font-semibold">{step.t}</h3>
                  <p className="text-sm text-muted-foreground">{step.d}</p>
                </div>
                <Check className="ml-auto h-5 w-5 shrink-0 text-success" />
              </Card>
            ))}
          </div>
          <div className="mt-12 flex justify-center gap-3">
            <Button asChild size="lg">
              <Link to="/signup">
                Create free account <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to={dashboardDestination}>
                <Database className="mr-2 h-4 w-4" />
                Open dashboard
              </Link>
            </Button>
          </div>
        </div>
      </section>

      <footer className="border-t border-border/60 bg-card/40">
        <div className="mx-auto grid max-w-6xl gap-10 px-6 py-12 md:grid-cols-[1.5fr_1fr_1fr]">
          <div>
            <div className="flex items-center gap-2 font-semibold tracking-tight">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-primary shadow-glow">
                <Shield className="h-4 w-4 text-primary-foreground" />
              </div>
              <span>PhishGuard</span>
            </div>
            <p className="mt-4 max-w-md text-sm text-muted-foreground">
              Production-ready phishing detection with a Flask ML API, Supabase auth, and a modern
              dashboard for scans, history, and admin analytics.
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-foreground">Quick links</h3>
            <div className="mt-4 flex flex-col gap-2 text-sm text-muted-foreground">
              <Link to="/signup" className="transition-colors hover:text-foreground">
                Create account
              </Link>
              <Link to="/login" className="transition-colors hover:text-foreground">
                Log in
              </Link>
              <Link to={dashboardDestination} className="transition-colors hover:text-foreground">
                Dashboard
              </Link>
              <Link to="/privacy" className="transition-colors hover:text-foreground">
                Privacy Policy
              </Link>
              <Link to="/terms" className="transition-colors hover:text-foreground">
                Terms of Service
              </Link>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-foreground">Platform</h3>
            <div className="mt-4 space-y-2 text-sm text-muted-foreground">
              <p>URL scanning and phishing Perdicts</p>
              <p>User scan history and exports</p>
              <p>Admin analytics and auth monitoring</p>
            </div>
          </div>
        </div>

        <div className="border-t border-border/60">
          <div className="mx-auto flex max-w-6xl flex-col gap-2 px-6 py-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
            <p>PhishGuard - built for safer browsing.</p>
            <p>&copy; {new Date().getFullYear()} PhishGuard. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
