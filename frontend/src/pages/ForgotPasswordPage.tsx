import { Link } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { Mail, Shield } from "lucide-react";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { getPasswordResetRequestErrorMessage } from "@/lib/auth-errors";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [emailSent, setEmailSent] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const normalizedEmail = email.trim().toLowerCase();

    setError(null);
    setEmailSent(null);

    if (!normalizedEmail) {
      setError("Email is required.");
      return;
    }

    setLoading(true);

    const redirectTo =
      typeof window === "undefined" ? undefined : `${window.location.origin}/reset-password`;
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(normalizedEmail, {
      redirectTo,
    });

    setLoading(false);

    if (resetError) {
      setError(getPasswordResetRequestErrorMessage(resetError));
      return;
    }

    setEmailSent(normalizedEmail);
    toast.success("If an account exists for that email, a reset link has been sent.");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-hero px-4 py-12">
      <Card className="w-full max-w-md border-border/60 bg-card/80 p-8 shadow-card backdrop-blur">
        <Link to="/" className="mb-6 flex items-center justify-center gap-2 font-semibold">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-primary shadow-glow">
            <Shield className="h-4 w-4 text-primary-foreground" />
          </div>
          PhishGuard
        </Link>
        <h1 className="text-center text-2xl font-bold tracking-tight">Reset your password</h1>
        <p className="mt-1 text-center text-sm text-muted-foreground">
          Enter your email and we&apos;ll send you a reset link.
        </p>
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setError(null);
                setEmailSent(null);
              }}
              className="mt-1.5"
            />
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {emailSent ? (
            <p className="rounded-md border border-primary/20 bg-primary/5 px-3 py-2 text-sm text-muted-foreground">
              Check <span className="font-medium text-foreground">{emailSent}</span> for the reset
              link.
            </p>
          ) : null}
          <Button type="submit" disabled={loading} className="w-full shadow-glow">
            <Mail className="h-4 w-4" />
            {loading ? "Sending..." : "Send reset link"}
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-muted-foreground">
          Remembered it?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Back to login
          </Link>
        </p>
      </Card>
    </div>
  );
}
