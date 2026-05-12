import { useCallback, useEffect, useState } from "react";
import { Activity, AlertTriangle, Clock3, Shield, Sparkles, TrendingUp, Users } from "lucide-react";
import { Header } from "@/components/Header";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  fetchAdminStats,
  fetchAdminUserHistory,
  type AdminRange,
  type AdminStatsResponse,
  type AdminUserHistoryResponse,
} from "@/services/api";

const RANGE_OPTIONS: Array<{ value: AdminRange; label: string }> = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
];

function formatTimestamp(value?: string) {
  if (!value) return "Never";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function formatDay(value?: string) {
  if (!value) return "-";

  const date = new Date(/^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T00:00:00` : value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  }).format(date);
}

function formatConfidence(value?: number | null) {
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "-";
}

function getPerdictClasses(result: "phishing" | "legit") {
  return result === "phishing"
    ? "border-destructive/20 bg-destructive/10 text-destructive"
    : "border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400";
}

export function AdminPage() {
  const [range, setRange] = useState<AdminRange>("30d");
  const [adminData, setAdminData] = useState<AdminStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [selectedUserError, setSelectedUserError] = useState<string | null>(null);
  const [selectedUserLoadingId, setSelectedUserLoadingId] = useState<string | null>(null);
  const [userHistoryById, setUserHistoryById] = useState<Record<string, AdminUserHistoryResponse>>(
    {},
  );

  const loadAdminData = useCallback(async (nextRange: AdminRange) => {
    setLoading(true);
    setError(null);

    try {
      setAdminData(await fetchAdminStats(nextRange));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Failed to load admin data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAdminData(range);
  }, [loadAdminData, range]);

  const summary = adminData?.summary;
  const overview = adminData?.overview;
  const users = adminData?.users ?? [];
  const activity = adminData?.activity ?? [];
  const topRiskyUrls = adminData?.topRiskyUrls ?? [];
  const recentScans = adminData?.recentScans ?? [];
  const userHistories = adminData?.userHistories ?? {};
  const selectedUser = users.find((entry) => entry.id === selectedUserId) ?? null;
  const selectedUserFallbackScans = selectedUserId ? (userHistories[selectedUserId] ?? []) : [];
  const selectedUserLoadedHistory = selectedUserId
    ? (userHistoryById[selectedUserId] ?? null)
    : null;
  const selectedUserScans = selectedUserLoadedHistory?.items ?? selectedUserFallbackScans;
  const maxDailyTotal = activity.reduce((largest, item) => Math.max(largest, item.total), 0);
  const selectedUserPhishingCount = selectedUserScans.filter(
    (scan) => scan.result === "phishing",
  ).length;
  const selectedUserLegitCount = selectedUserScans.filter((scan) => scan.result === "legit").length;
  const selectedUserTotalScans = selectedUserLoadedHistory?.total ?? selectedUserScans.length;

  const loadSelectedUserHistory = useCallback(
    async (userId: string | null) => {
      if (!userId || userHistoryById[userId]) {
        return;
      }

      setSelectedUserError(null);
      setSelectedUserLoadingId(userId);

      try {
        const history = await fetchAdminUserHistory(userId);
        setUserHistoryById((current) => ({ ...current, [userId]: history }));
      } catch (requestError) {
        if ((userHistories[userId] ?? []).length === 0) {
          setSelectedUserError(
            requestError instanceof Error
              ? requestError.message
              : "Failed to load user scan history.",
          );
        }
      } finally {
        setSelectedUserLoadingId((current) => (current === userId ? null : current));
      }
    },
    [userHistories, userHistoryById],
  );

  useEffect(() => {
    void loadSelectedUserHistory(selectedUserId);
  }, [loadSelectedUserHistory, selectedUserId]);

  const heroStats = [
    {
      label: "Users",
      value: summary?.totalUsers ?? 0,
      hint: `${summary?.adminUsers ?? 0} admins`,
      icon: Users,
    },
    {
      label: "Scans",
      value: overview?.totalScans ?? 0,
      hint: `${overview?.uniqueUsers ?? 0} active users`,
      icon: Activity,
    },
    {
      label: "Threats found",
      value: overview?.phishingCount ?? 0,
      hint: `${overview?.legitCount ?? 0} legit scans`,
      icon: AlertTriangle,
    },
    {
      label: "Avg confidence",
      value: formatConfidence(overview?.avgConfidence),
      hint: `Updated for ${RANGE_OPTIONS.find((option) => option.value === range)?.label ?? range}`,
      icon: TrendingUp,
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="mx-auto max-w-7xl px-6 py-12">
        <ProtectedRoute requireAdmin>
          <div className="space-y-6">
            <Card className="overflow-hidden border-border/60 bg-gradient-hero shadow-card">
              <CardContent className="p-0">
                <div className="grid gap-8 p-6 lg:grid-cols-[1.2fr_0.8fr] lg:p-8">
                  <div className="space-y-5">
                    <Badge variant="secondary" className="w-fit bg-card/70 backdrop-blur">
                      <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                      Platform control center
                    </Badge>
                    <div>
                      <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
                        Admin overview
                      </h1>
                      <p className="mt-3 max-w-2xl text-sm text-muted-foreground sm:text-base">
                        A cleaner snapshot of user access, phishing trends, and recent platform
                        activity.
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {RANGE_OPTIONS.map((option) => (
                        <Button
                          key={option.value}
                          variant={range === option.value ? "default" : "outline"}
                          size="sm"
                          className={range === option.value ? "shadow-glow" : "bg-background/70"}
                          onClick={() => setRange(option.value)}
                          disabled={loading}
                        >
                          {option.label}
                        </Button>
                      ))}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="bg-background/50"
                        onClick={() => void loadAdminData(range)}
                        disabled={loading}
                      >
                        {loading ? "Refreshing..." : "Refresh"}
                      </Button>
                    </div>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    {heroStats.map(({ label, value, hint, icon: Icon }) => (
                      <div
                        key={label}
                        className="rounded-2xl border border-border/60 bg-card/70 p-4 backdrop-blur"
                      >
                        <div className="flex items-center justify-between">
                          <p className="text-sm text-muted-foreground">{label}</p>
                          <div className="rounded-full bg-primary/10 p-2 text-primary">
                            <Icon className="h-4 w-4" />
                          </div>
                        </div>
                        <p className="mt-4 text-2xl font-semibold tracking-tight">{value}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {error ? (
              <Card className="border-destructive/40 bg-destructive/5">
                <CardContent className="p-6">
                  <p className="text-sm text-destructive">{error}</p>
                </CardContent>
              </Card>
            ) : null}

            <Tabs defaultValue="overview" className="space-y-6">
              <TabsList className="grid w-full max-w-md grid-cols-3">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="history">History</TabsTrigger>
                <TabsTrigger value="users">Users</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-6">
                <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
                  <Card className="border-border/60 shadow-card">
                    <CardHeader>
                      <CardTitle>Daily activity</CardTitle>
                      <CardDescription>
                        Simple per-day scan volume with phishing vs legit mix.
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {activity.length > 0 ? (
                          activity.map((item) => {
                            const phishingWidth =
                              item.total > 0 ? `${(item.phishing / item.total) * 100}%` : "0%";
                            const legitWidth =
                              item.total > 0 ? `${(item.legit / item.total) * 100}%` : "0%";
                            const totalWidth =
                              maxDailyTotal > 0 ? `${(item.total / maxDailyTotal) * 100}%` : "0%";

                            return (
                              <div key={item.date} className="space-y-2 rounded-xl bg-muted/40 p-3">
                                <div className="flex items-center justify-between gap-3">
                                  <div>
                                    <p className="font-medium">{formatDay(item.date)}</p>
                                    <p className="text-xs text-muted-foreground">
                                      {item.total} total scans
                                    </p>
                                  </div>
                                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                    <span>{item.phishing} phishing</span>
                                    <span>{item.legit} legit</span>
                                  </div>
                                </div>
                                <div className="h-2 rounded-full bg-background">
                                  <div
                                    className="flex h-2 overflow-hidden rounded-full"
                                    style={{ width: totalWidth }}
                                  >
                                    <div
                                      className="h-full bg-destructive/80"
                                      style={{ width: phishingWidth }}
                                    />
                                    <div
                                      className="h-full bg-emerald-500/80"
                                      style={{ width: legitWidth }}
                                    />
                                  </div>
                                </div>
                              </div>
                            );
                          })
                        ) : (
                          <p className="text-sm text-muted-foreground">
                            {loading ? "Loading activity..." : "No daily activity in this range."}
                          </p>
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  <div className="space-y-6">
                    <Card className="border-border/60 shadow-card">
                      <CardHeader>
                        <CardTitle>Top risky URLs</CardTitle>
                        <CardDescription>The URLs most often flagged as phishing.</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {topRiskyUrls.length > 0 ? (
                          topRiskyUrls.slice(0, 5).map((item, index) => (
                            <div
                              key={`${item.url}-${item.lastSeen ?? "never"}`}
                              className="space-y-3"
                            >
                              <div className="flex items-start gap-3">
                                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
                                  {index + 1}
                                </div>
                                <div className="min-w-0 flex-1">
                                  <p className="break-all text-sm font-medium">{item.url}</p>
                                  <p className="mt-1 text-xs text-muted-foreground">
                                    {item.count} alerts • last seen {formatTimestamp(item.lastSeen)}
                                  </p>
                                </div>
                              </div>
                              {index < Math.min(topRiskyUrls.length, 5) - 1 ? <Separator /> : null}
                            </div>
                          ))
                        ) : (
                          <p className="text-sm text-muted-foreground">
                            {loading
                              ? "Loading risky URLs..."
                              : "No phishing URLs found in this range."}
                          </p>
                        )}
                      </CardContent>
                    </Card>

                    <Card className="border-border/60 shadow-card">
                      <CardHeader>
                        <CardTitle>Access snapshot</CardTitle>
                        <CardDescription>
                          Quick view of current admin access and sign-in activity.
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="grid gap-4 sm:grid-cols-2">
                        <div className="rounded-2xl bg-muted/40 p-4">
                          <p className="text-sm text-muted-foreground">Admin accounts</p>
                          <p className="mt-2 text-2xl font-semibold">{summary?.adminUsers ?? 0}</p>
                        </div>
                        <div className="rounded-2xl bg-muted/40 p-4">
                          <p className="text-sm text-muted-foreground">Standard accounts</p>
                          <p className="mt-2 text-2xl font-semibold">
                            {summary?.standardUsers ?? 0}
                          </p>
                        </div>
                        <div className="rounded-2xl bg-muted/40 p-4 sm:col-span-2">
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Clock3 className="h-4 w-4" />
                            Latest sign-in
                          </div>
                          <p className="mt-2 font-medium">
                            {formatTimestamp(summary?.mostRecentSignIn)}
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="history">
                <Card className="border-border/60 shadow-card">
                  <CardHeader>
                    <CardTitle>Recent scan history</CardTitle>
                    <CardDescription>
                      The latest activity across the platform for the selected range.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-[420px] pr-4">
                      <div className="space-y-3">
                        {recentScans.length > 0 ? (
                          recentScans.map((scan) => (
                            <div
                              key={
                                scan.id ?? `${scan.url}-${scan.created_at ?? scan.userId ?? "scan"}`
                              }
                              className="rounded-2xl border border-border/60 bg-card/50 p-4"
                            >
                              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                <div className="min-w-0 flex-1">
                                  <p className="break-all font-medium">{scan.url}</p>
                                  <p className="mt-1 text-sm text-muted-foreground">
                                    {scan.userEmail ?? scan.userId ?? "Unknown user"}
                                  </p>
                                </div>
                                <Badge className={getPerdictClasses(scan.result)}>
                                  {scan.result === "phishing" ? "Phishing" : "Legit"}
                                </Badge>
                              </div>
                              <div className="mt-4 flex flex-wrap gap-4 text-sm text-muted-foreground">
                                <span>Confidence: {formatConfidence(scan.confidence)}</span>
                                <span>Scanned: {formatTimestamp(scan.created_at)}</span>
                              </div>
                            </div>
                          ))
                        ) : (
                          <p className="text-sm text-muted-foreground">
                            {loading
                              ? "Loading recent history..."
                              : "No recent scan history in this range."}
                          </p>
                        )}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="users">
                <Card className="border-border/60 shadow-card">
                  <CardHeader>
                    <CardTitle>User access</CardTitle>
                    <CardDescription>
                      Click a user to see all recorded scans with phishing and legit results.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-5">
                    <div className="flex flex-wrap items-center gap-2 rounded-2xl bg-muted/40 p-3 text-sm text-muted-foreground">
                      <Badge variant="secondary" className="rounded-full">
                        {users.length} accounts
                      </Badge>
                      <span>Simple list for opening each user's scan history.</span>
                    </div>

                    <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
                      <ScrollArea className="h-[520px] pr-4">
                        <div className="space-y-3">
                          {users.length > 0 ? (
                            users.map((user) => {
                              const isSelected = user.id === selectedUserId;
                              return (
                                <button
                                  key={user.id ?? user.email ?? "user-card"}
                                  type="button"
                                  onClick={() => setSelectedUserId(user.id ?? null)}
                                  className={`w-full rounded-2xl border p-4 text-left shadow-sm transition-colors ${
                                    isSelected
                                      ? "border-primary/50 bg-primary/5"
                                      : "border-border/60 bg-card/60 hover:bg-card/80"
                                  }`}
                                >
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                      <p className="break-all font-semibold">
                                        {user.email ?? user.id ?? "Unknown user"}
                                      </p>
                                      <p className="mt-1 text-sm text-muted-foreground">
                                        {user.lastSignInTimestamp
                                          ? `Last sign-in ${formatTimestamp(user.lastSignInTimestamp)}`
                                          : "No sign-in activity yet"}
                                      </p>
                                    </div>
                                    <Badge
                                      variant={user.role === "admin" ? "default" : "secondary"}
                                      className="rounded-full capitalize"
                                    >
                                      {user.role}
                                    </Badge>
                                  </div>
                                </button>
                              );
                            })
                          ) : (
                            <p className="text-sm text-muted-foreground">
                              {loading ? "Loading users..." : "No user activity available."}
                            </p>
                          )}
                        </div>
                      </ScrollArea>

                      <div className="rounded-2xl border border-border/60 bg-card/50">
                        <div className="border-b border-border/60 p-5">
                          <h3 className="text-lg font-semibold">User scans</h3>
                          <p className="mt-1 text-sm text-muted-foreground">
                            {selectedUser
                              ? (selectedUser.email ?? selectedUser.id ?? "Selected user")
                              : "Choose a user from the list to view scans."}
                          </p>
                        </div>
                        <div className="p-5">
                          {!selectedUser ? (
                            <p className="text-sm text-muted-foreground">
                              Select a user to load all recorded scans.
                            </p>
                          ) : selectedUserError ? (
                            <p className="text-sm text-destructive">{selectedUserError}</p>
                          ) : (
                            <div className="space-y-4">
                              <div className="flex flex-wrap gap-2">
                                <Badge variant="secondary" className="rounded-full">
                                  {selectedUserTotalScans} scans
                                </Badge>
                                <Badge className="rounded-full border-destructive/20 bg-destructive/10 text-destructive">
                                  {selectedUserPhishingCount} phishing
                                </Badge>
                                <Badge className="rounded-full border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
                                  {selectedUserLegitCount} legit
                                </Badge>
                              </div>

                              <ScrollArea className="h-[420px] pr-4">
                                <div className="space-y-3">
                                  {selectedUserLoadingId === selectedUser.id &&
                                  selectedUserScans.length === 0 ? (
                                    <p className="text-sm text-muted-foreground">
                                      Loading scans...
                                    </p>
                                  ) : selectedUserScans.length > 0 ? (
                                    selectedUserScans.map((scan) => (
                                      <div
                                        key={
                                          scan.id ??
                                          `${scan.url}-${scan.created_at ?? scan.userId ?? "scan"}`
                                        }
                                        className="rounded-2xl border border-border/60 bg-card/60 p-4"
                                      >
                                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                          <div className="min-w-0 flex-1">
                                            <p className="break-all font-medium">{scan.url}</p>
                                            <p className="mt-1 text-sm text-muted-foreground">
                                              {formatTimestamp(scan.created_at)}
                                            </p>
                                          </div>
                                          <Badge className={getPerdictClasses(scan.result)}>
                                            {scan.result === "phishing" ? "Phishing" : "Legit"}
                                          </Badge>
                                        </div>
                                        <div className="mt-4 text-sm text-muted-foreground">
                                          Confidence: {formatConfidence(scan.confidence)}
                                        </div>
                                      </div>
                                    ))
                                  ) : (
                                    <p className="text-sm text-muted-foreground">
                                      No scans were found for this user.
                                    </p>
                                  )}
                                </div>
                              </ScrollArea>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>

            <Card className="border-border/60 bg-card/60 shadow-card">
              <CardContent className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-primary" />
                    <p className="font-medium">Admin workspace</p>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Designed to keep the most important analytics visible without overwhelming the
                    page.
                  </p>
                </div>
                <Badge variant="outline">{users.length} tracked accounts</Badge>
              </CardContent>
            </Card>
          </div>
        </ProtectedRoute>
      </main>
    </div>
  );
}
