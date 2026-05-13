import { useState, type FormEvent } from "react";
import { KeyRound } from "lucide-react";
import { toast } from "sonner";
import { Header } from "@/components/Header";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";
import { supabase } from "@/integrations/supabase/client";
import { getCurrentPasswordErrorMessage, getPasswordUpdateErrorMessage } from "@/lib/auth-errors";
import { getPasswordValidationError } from "@/lib/password-validation";

export function SettingsPage() {
  const { user, isAdmin } = useAuth();
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  async function onChangePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordError(null);

    if (!user?.email) {
      setPasswordError("Please sign in again.");
      return;
    }

    if (!currentPassword) {
      setPasswordError("Current password is required.");
      return;
    }

    const passwordValidationError = getPasswordValidationError(newPassword, confirmPassword);
    if (passwordValidationError) {
      setPasswordError(passwordValidationError.message);
      return;
    }

    setPasswordSaving(true);
    const { error: currentPasswordError } = await supabase.auth.signInWithPassword({
      email: user.email,
      password: currentPassword,
    });

    if (currentPasswordError) {
      setPasswordSaving(false);
      setPasswordError(getCurrentPasswordErrorMessage(currentPasswordError));
      return;
    }

    const { error } = await supabase.auth.updateUser({ password: newPassword });
    setPasswordSaving(false);

    if (error) {
      setPasswordError(getPasswordUpdateErrorMessage(error));
      return;
    }

    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    toast.success("Password updated.");
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="mx-auto max-w-5xl px-6 py-12">
        <ProtectedRoute>
          <div className="space-y-6">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Manage your password for your {isAdmin ? "admin" : "user"} account.
              </p>
            </div>

            <Card className="border-border/60 shadow-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <KeyRound className="h-5 w-5" />
                  Password
                </CardTitle>
                <CardDescription>
                  Choose a strong password to keep your account secure.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={onChangePassword} className="space-y-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="email">Email</Label>
                    <Input id="email" value={user?.email ?? ""} disabled readOnly />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="current-password">Current password</Label>
                    <Input
                      id="current-password"
                      type="password"
                      value={currentPassword}
                      onChange={(event) => {
                        setCurrentPassword(event.target.value);
                        setPasswordError(null);
                      }}
                      autoComplete="current-password"
                      placeholder="Enter your current password"
                      disabled={passwordSaving}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="new-password">New password</Label>
                    <Input
                      id="new-password"
                      type="password"
                      value={newPassword}
                      onChange={(event) => {
                        setNewPassword(event.target.value);
                        setPasswordError(null);
                      }}
                      minLength={6}
                      autoComplete="new-password"
                      placeholder="At least 6 characters"
                      disabled={passwordSaving}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="confirm-password">Confirm new password</Label>
                    <Input
                      id="confirm-password"
                      type="password"
                      value={confirmPassword}
                      onChange={(event) => {
                        setConfirmPassword(event.target.value);
                        setPasswordError(null);
                      }}
                      minLength={6}
                      autoComplete="new-password"
                      placeholder="Re-enter your new password"
                      disabled={passwordSaving}
                    />
                  </div>
                  {passwordError ? (
                    <p className="text-sm text-destructive">{passwordError}</p>
                  ) : null}
                  <Button type="submit" disabled={passwordSaving}>
                    <KeyRound className="h-4 w-4" />
                    {passwordSaving ? "Updating..." : "Update password"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </ProtectedRoute>
      </main>
    </div>
  );
}
