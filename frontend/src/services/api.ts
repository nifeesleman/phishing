import { supabase } from "@/integrations/supabase/client";

export type Prediction = "phishing" | "safe" | "unavailable";

export type PredictionResponse = {
  prediction: Prediction;
  result: "phishing" | "legit" | "unavailable";
  confidence: number | null;
  modelName: string | null;
  modelVersion: string | null;
  message: string | null;
};

export type HistorySort = "newest" | "oldest" | "confidence_desc" | "confidence_asc";

export type HistoryItem = {
  id?: string;
  userId?: string;
  userEmail?: string | null;
  url: string;
  result: "phishing" | "legit";
  confidence: number | null;
  created_at?: string;
};

export type HistoryResponse = {
  items: HistoryItem[];
  total: number;
  pagination: {
    limit: number;
    offset: number;
  };
};

export type HistoryFilters = {
  limit: number;
  offset: number;
  search: string;
  result: "" | "phishing" | "legit";
  sort: HistorySort;
};

export type AdminRange = "7d" | "30d" | "90d";

export type AdminUser = {
  id?: string;
  email?: string | null;
  phone?: string | null;
  role: "admin" | "standard";
  signupTimestamp?: string;
  lastSignInTimestamp?: string;
  emailConfirmedTimestamp?: string;
  providers: string[];
};

export type AdminDirectoryResponse = {
  users: AdminUser[];
  summary: {
    totalUsers: number;
    adminUsers: number;
    standardUsers: number;
    mostRecentSignIn?: string;
  };
};

export type AdminInactiveCleanupFailure = AdminUser & {
  message: string;
};

export type AdminInactiveCleanupResponse = {
  cutoffTimestamp?: string;
  deletedCount: number;
  failedCount: number;
  deletedUsers: AdminUser[];
  failedUsers: AdminInactiveCleanupFailure[];
};

export type AdminOverview = {
  totalScans: number;
  phishingCount: number;
  legitCount: number;
  uniqueUsers: number;
  avgConfidence: number;
};

export type AdminActivityItem = {
  date: string;
  total: number;
  phishing: number;
  legit: number;
};

export type AdminRiskyUrl = {
  url: string;
  count: number;
  result: "phishing";
  lastSeen?: string;
};

export type AdminStatsResponse = AdminDirectoryResponse & {
  range: AdminRange;
  overview: AdminOverview;
  activity: AdminActivityItem[];
  topRiskyUrls: AdminRiskyUrl[];
  recentScans: HistoryItem[];
  userHistories: Record<string, HistoryItem[]>;
};

export type AdminUserHistoryResponse = {
  items: HistoryItem[];
  total: number;
};

function normalizeUserHistories(value: unknown) {
  const entries = asObject(value) ?? {};
  return Object.fromEntries(
    Object.entries(entries).map(([userId, history]) => [
      userId,
      Array.isArray(history) ? history.map(normalizeHistoryItem) : [],
    ]),
  );
}

type RequestOptions = {
  method?: "GET" | "POST";
  body?: unknown;
  query?: Record<string, string | number | undefined>;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status = 500) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function getApiBaseUrl() {
  const rawBaseUrl =
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.VITE_API_URL ||
    import.meta.env.VITE_FLASK_API_BASE_URL ||
    process.env.API_URL ||
    process.env.API_BASE_URL ||
    process.env.FLASK_API_BASE_URL;

  if (rawBaseUrl) {
    return rawBaseUrl.replace(/\/+$/, "");
  }

  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:5000`;
  }

  throw new ApiError(
    "Missing backend URL. Set VITE_API_BASE_URL or VITE_API_URL to your Flask API base URL.",
    500,
  );
}

function asObject(value: unknown) {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : null;
}

function toString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function toStringArray(value: unknown) {
  return Array.isArray(value)
    ? value.filter((entry): entry is string => typeof entry === "string")
    : [];
}

function toPrediction(value: unknown): Prediction {
  if (value === "phishing") return "phishing";
  if (value === "unavailable") return "unavailable";
  return "safe";
}

function normalizeHistoryItem(value: unknown): HistoryItem {
  const entry = asObject(value) ?? {};
  return {
    id: toString(entry.id) || undefined,
    userId: toString(entry.user_id) || undefined,
    userEmail: toString(entry.user_email || entry.email) || undefined,
    url: toString(entry.url),
    result: entry.result === "phishing" ? "phishing" : "legit",
    confidence:
      typeof entry.confidence === "number"
        ? entry.confidence
        : typeof entry.confidence_score === "number"
          ? entry.confidence_score
          : null,
    created_at: toString(entry.created_at) || undefined,
  } satisfies HistoryItem;
}

function normalizeAdminUser(value: unknown): AdminUser {
  const entry = asObject(value) ?? {};
  return {
    id: toString(entry.id) || undefined,
    email: toString(entry.email) || undefined,
    phone: toString(entry.phone) || undefined,
    role: entry.is_admin === true ? "admin" : "standard",
    signupTimestamp: toString(entry.signup_timestamp) || undefined,
    lastSignInTimestamp: toString(entry.last_sign_in_timestamp) || undefined,
    emailConfirmedTimestamp: toString(entry.email_confirmed_timestamp) || undefined,
    providers: toStringArray(entry.providers),
  } satisfies AdminUser;
}

function summarizeAdminUsers(users: AdminUser[]) {
  const adminUsers = users.filter((user) => user.role === "admin").length;
  const mostRecentSignIn = users
    .map((user) => user.lastSignInTimestamp)
    .filter((value): value is string => Boolean(value))
    .sort((left, right) => right.localeCompare(left))[0];

  return {
    totalUsers: users.length,
    adminUsers,
    standardUsers: users.length - adminUsers,
    mostRecentSignIn,
  };
}

function normalizeAdminCleanupFailure(value: unknown): AdminInactiveCleanupFailure {
  const entry = asObject(value) ?? {};
  return {
    ...normalizeAdminUser(entry),
    message: toString(entry.message) || "Cleanup failed.",
  } satisfies AdminInactiveCleanupFailure;
}

async function getAccessToken() {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    throw new ApiError("Your session expired. Please sign in again.", 401);
  }

  return session.access_token;
}

async function parseApiError(response: Response) {
  let message = `Request failed with status ${response.status}`;

  try {
    const body = await response.clone().json();
    const record = asObject(body);
    const errorRecord = asObject(record?.error);
    message =
      toString(errorRecord?.message) ||
      toString(record?.message) ||
      toString(record?.error) ||
      message;
  } catch {
    const text = (await response.text()).trim();
    if (text) {
      message = text;
    }
  }

  return new ApiError(message, response.status);
}

async function request<T>(path: string, options: RequestOptions = {}) {
  const token = await getAccessToken();
  const url = new URL(`${getApiBaseUrl()}${path}`);

  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }

  const response = await fetch(url.toString(), {
    method: options.method ?? "GET",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  return (await response.json()) as T;
}

export async function predictUrl(url: string) {
  const payload = await request<unknown>("/predict", {
    method: "POST",
    body: { url },
  });
  const record = asObject(payload) ?? {};

  return {
    prediction: toPrediction(record.prediction),
    result:
      record.result === "phishing"
        ? "phishing"
        : record.result === "unavailable"
          ? "unavailable"
          : "legit",
    confidence: typeof record.confidence === "number" ? record.confidence : null,
    modelName: toString(record.model_name) || null,
    modelVersion: toString(record.model_version) || null,
    message: toString(record.message) || null,
  } satisfies PredictionResponse;
}

export async function fetchHistory(filters: HistoryFilters): Promise<HistoryResponse> {
  const payload = await request<unknown>("/history", {
    query: {
      limit: filters.limit,
      offset: filters.offset,
      search: filters.search || undefined,
      result: filters.result || undefined,
      sort: filters.sort,
    },
  });
  const record = asObject(payload) ?? {};
  const items = Array.isArray(record.items) ? record.items : [];
  const pagination = asObject(record.pagination) ?? {};

  return {
    items: items.map(normalizeHistoryItem),
    total: typeof record.total === "number" ? record.total : 0,
    pagination: {
      limit: typeof pagination.limit === "number" ? pagination.limit : filters.limit,
      offset: typeof pagination.offset === "number" ? pagination.offset : filters.offset,
    },
  };
}

export async function fetchAdminStats(range: AdminRange = "30d"): Promise<AdminStatsResponse> {
  const payload = await request<unknown>("/admin/stats", {
    query: {
      range,
      include_auth_history: "true",
    },
  });
  const record = asObject(payload) ?? {};
  const overview = asObject(record.overview) ?? {};
  const users = Array.isArray(record.auth_history)
    ? record.auth_history.map(normalizeAdminUser)
    : [];
  const activity = Array.isArray(record.activity) ? record.activity : [];
  const topRiskyUrls = Array.isArray(record.top_risky_urls) ? record.top_risky_urls : [];
  const recentScans = Array.isArray(record.recent_scans) ? record.recent_scans : [];
  const userHistories = normalizeUserHistories(record.user_histories);

  return {
    range,
    users,
    summary: summarizeAdminUsers(users),
    overview: {
      totalScans: typeof overview.total_scans === "number" ? overview.total_scans : 0,
      phishingCount: typeof overview.phishing_count === "number" ? overview.phishing_count : 0,
      legitCount: typeof overview.legit_count === "number" ? overview.legit_count : 0,
      uniqueUsers: typeof overview.unique_users === "number" ? overview.unique_users : 0,
      avgConfidence: typeof overview.avg_confidence === "number" ? overview.avg_confidence : 0,
    },
    activity: activity.map((value) => {
      const entry = asObject(value) ?? {};
      return {
        date: toString(entry.date),
        total: typeof entry.total === "number" ? entry.total : 0,
        phishing: typeof entry.phishing === "number" ? entry.phishing : 0,
        legit: typeof entry.legit === "number" ? entry.legit : 0,
      } satisfies AdminActivityItem;
    }),
    topRiskyUrls: topRiskyUrls.map((value) => {
      const entry = asObject(value) ?? {};
      return {
        url: toString(entry.url),
        count: typeof entry.count === "number" ? entry.count : 0,
        result: "phishing",
        lastSeen: toString(entry.last_seen) || undefined,
      } satisfies AdminRiskyUrl;
    }),
    recentScans: recentScans.map(normalizeHistoryItem),
    userHistories,
  };
}

export async function fetchAdminInactiveCleanup(): Promise<AdminInactiveCleanupResponse> {
  const payload = await request<unknown>("/admin/users/cleanup-inactive", {
    method: "POST",
  });
  const record = asObject(payload) ?? {};
  const deletedUsers = Array.isArray(record.deleted_users) ? record.deleted_users : [];
  const failedUsers = Array.isArray(record.failed_users) ? record.failed_users : [];

  return {
    cutoffTimestamp: toString(record.cutoff_timestamp) || undefined,
    deletedCount: typeof record.deleted_count === "number" ? record.deleted_count : 0,
    failedCount: typeof record.failed_count === "number" ? record.failed_count : 0,
    deletedUsers: deletedUsers.map(normalizeAdminUser),
    failedUsers: failedUsers.map(normalizeAdminCleanupFailure),
  };
}

export async function fetchAdminUserHistory(userId: string): Promise<AdminUserHistoryResponse> {
  const payload = await request<unknown>(`/admin/users/${encodeURIComponent(userId)}/history`);
  const record = asObject(payload) ?? {};
  const items = Array.isArray(record.items) ? record.items : [];

  return {
    items: items.map(normalizeHistoryItem),
    total: typeof record.total === "number" ? record.total : items.length,
  };
}
