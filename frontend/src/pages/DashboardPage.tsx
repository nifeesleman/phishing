import { useState, type FormEvent } from "react";
import { Header } from "@/components/Header";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, predictUrl, type PredictionResponse } from "@/services/api";

export function DashboardPage() {
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PredictionResponse | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const nextResult = await predictUrl(url.trim());
      setResult(nextResult);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError || requestError instanceof Error
          ? requestError.message
          : "Prediction failed.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="mx-auto max-w-4xl px-6 py-12">
        <ProtectedRoute>
          <div className="space-y-6">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Submit a URL to the Flask prediction API. Your Supabase session token is sent in the
                authorization header automatically.
              </p>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Check a URL</CardTitle>
                <CardDescription>Example: https://example.com/login</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={onSubmit} className="space-y-4">
                  <Input
                    type="text"
                    placeholder="https://example.com/login"
                    value={url}
                    onChange={(event) => setUrl(event.target.value)}
                    required
                  />
                  <Button type="submit" disabled={submitting || !url.trim()}>
                    {submitting ? "Checking..." : "Predict"}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {error ? (
              <Card className="border-destructive/40">
                <CardContent className="p-6">
                  <p className="text-sm text-destructive">{error}</p>
                </CardContent>
              </Card>
            ) : null}

            {result ? (
              <Card>
                <CardHeader>
                  <CardTitle>Prediction result</CardTitle>
                  <CardDescription>The backend returns the Perdict and confidence score.</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-lg border border-border/60 bg-card p-4">
                      <p className="text-sm text-muted-foreground">Perdict</p>
                      <p className="mt-2 text-2xl font-semibold capitalize">
                        {result.prediction === "unavailable" ? "Site unavailable" : result.prediction}
                      </p>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-card p-4">
                      <p className="text-sm text-muted-foreground">Confidence</p>
                      <p className="mt-2 text-2xl font-semibold">
                        {result.confidence !== null ? `${(result.confidence * 100).toFixed(2)}%` : "Unavailable"}
                      </p>
                    </div>
                  </div>
                  {result.message ? (
                    <p className="mt-4 text-sm text-muted-foreground">{result.message}</p>
                  ) : null}
                </CardContent>
              </Card>
            ) : null}
          </div>
        </ProtectedRoute>
      </main>
    </div>
  );
}
