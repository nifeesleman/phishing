import { Link } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";
import { Loader2, Shield, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { getPasswordUpdateErrorMessage } from "@/lib/auth-errors";
import { getPasswordValidationError } from "@/lib/password-validation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function hasRecoveryParams() {
  if (typeof window === "undefined") {
    return false;
  }

  const searchParams = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));

  return (
    searchParams.get("type") === "recovery" ||
    hashParams.get("type") === "recovery" ||
    Boolean(searchParams.get("code")) ||
    Boolean(searchParams.get("token_hash")) ||
    Boolean(hashParams.get("access_token")) ||
    Boolean(hashParams.get("refresh_token"))
  );
}

export function ResetPasswordPage() {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recoveryReady, setRecoveryReady] = useState(false);
  const [checkingRecovery, setCheckingRecovery] = useState(true);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    let active = true;
    const hasRecoveryLink = hasRecoveryParams();

    const finishChecking = (isReady: boolean) => {
      if (!active) {
        return;
      }

      setRecoveryReady(isReady);
      setCheckingRecovery(false);
    };

    const timeoutId = hasRecoveryLink
      ? window.setTimeout(() => finishChecking(false), 3000)
      : undefined;

    const { data } = supabase.auth.onAuthStateChange((event, nextSession) => {
      if (!active) {
        return;
      }

      if (event === "PASSWORD_RECOVERY" && nextSession?.user) {
        if (timeoutId) {
          window.clearTimeout(timeoutId);
        }
        finishChecking(true);
      }
    });

    void supabase.auth.getSession().then(({ data: { session } }) => {
      if (!active) {
        return;
      }

      if (session?.user && hasRecoveryLink) {
        if (timeoutId) {
          window.clearTimeout(timeoutId);
        }
        finishChecking(true);
        return;
      }

      if (!hasRecoveryLink) {
        finishChecking(false);
      }
    });

    return () => {
      active = false;
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
      data.subscription.unsubscribe();
    };
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    const validationError = getPasswordValidationError(password, confirmPassword);
    if (validationError) {
      setError(validationError.message);
      return;
    }

    setSaving(true);
    const { error: updateError } = await supabase.auth.updateUser({ password });

    if (updateError) {
      setSaving(false);
      setError(getPasswordUpdateErrorMessage(updateError));
      return;
    }

    await supabase.auth.signOut();
    toast.success("Password updated. Please log in with your new password.");
    window.location.replace("/login");
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
        <h1 className="text-center text-2xl font-bold tracking-tight">Choose a new password</h1>
        <p className="mt-1 text-center text-sm text-muted-foreground">
          Use a strong password you haven&apos;t used before.
        </p>
        {checkingRecovery ? (
          <div className="mt-6 flex flex-col items-center gap-3 rounded-md border border-border/60 bg-background/40 px-4 py-6 text-center">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Validating your reset link...</p>
          </div>
        ) : recoveryReady ? (
          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <Label htmlFor="password">New password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                required
                minLength={6}
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value);
                  setError(null);
                }}
                className="mt-1.5"
              />
            </div>
            <div>
              <Label htmlFor="confirm-password">Confirm new password</Label>
              <Input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                required
                minLength={6}
                value={confirmPassword}
                onChange={(event) => {
                  setConfirmPassword(event.target.value);
                  setError(null);
                }}
                className="mt-1.5"
              />
            </div>
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            <Button type="submit" disabled={saving} className="w-full shadow-glow">
              {saving ? "Updating..." : "Update password"}
            </Button>
          </form>
        ) : (
          <div className="mt-6 rounded-md border border-border/60 bg-background/40 px-4 py-6 text-center">
            <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
              This reset link is missing or has expired. Request a new one to continue.
            </p>
            <div className="mt-4 flex justify-center">
              <Button asChild>
                <Link to="/forgot-password">Request another link</Link>
              </Button>
            </div>
          </div>
        )}
        <p className="mt-6 text-center text-sm text-muted-foreground">
          <Link to="/login" className="font-medium text-primary hover:underline">
            Back to login
          </Link>
        </p>
      </Card>
    </div>
  );
}
