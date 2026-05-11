import { Link, useRouterState } from "@tanstack/react-router";
import { Shield } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { Button, buttonVariants } from "@/components/ui/button";
import { getDefaultAuthenticatedPath } from "@/lib/auth-navigation";
import { cn } from "@/lib/utils";

export function Header() {
  const { user, isAdmin, signOut } = useAuth();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const brandDestination = user ? getDefaultAuthenticatedPath(isAdmin) : "/";
  const hideUserNavForAdmin = isAdmin && (pathname === "/admin" || pathname === "/settings");

  return (
    <header className="border-b border-border/60 bg-card/60">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
        <Link to={brandDestination} className="flex items-center gap-2 text-lg font-semibold">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-primary">
            <Shield className="h-4 w-4 text-primary-foreground" />
          </span>
          PhishGuard
        </Link>

        <nav className="flex items-center gap-2">
          {user ? (
            <>
              {!hideUserNavForAdmin ? (
                <>
                  <Link
                    to="/dashboard"
                    className={cn(
                      buttonVariants({
                        variant: pathname === "/dashboard" ? "secondary" : "ghost",
                        size: "sm",
                      }),
                    )}
                  >
                    Dashboard
                  </Link>
                  <Link
                    to="/history"
                    className={cn(
                      buttonVariants({
                        variant: pathname === "/history" ? "secondary" : "ghost",
                        size: "sm",
                      }),
                    )}
                  >
                    History
                  </Link>
                </>
              ) : null}
              <Link
                to="/settings"
                className={cn(
                  buttonVariants({
                    variant: pathname === "/settings" ? "secondary" : "ghost",
                    size: "sm",
                  }),
                )}
              >
                Settings
              </Link>
              {isAdmin ? (
                <Link
                  to="/admin"
                  className={cn(
                    buttonVariants({
                      variant: pathname === "/admin" ? "secondary" : "ghost",
                      size: "sm",
                    }),
                  )}
                >
                  Admin
                </Link>
              ) : null}
              <Button variant="outline" size="sm" onClick={() => void signOut("/")}>
                Sign out
              </Button>
            </>
          ) : (
            <>
              <Link to="/login" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}>
                Log in
              </Link>
              <Link to="/signup" className={cn(buttonVariants({ size: "sm" }))}>
                Register
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
