import type {
  DashboardStats,
  Problem,
  RecommendationResponse,
  TopicStat,
  SolveLogEntry,
  UserSettings,
  Note,
  SyncStatus,
  AuthUser,
  TokenResponse,
} from "./types";
import { notifyDataChanged } from "./dataEvents";
import { clearToken, getToken, setToken } from "./auth";

const BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

// Dispatched whenever a request comes back 401 -- the token is missing,
// expired, or otherwise invalid. AuthContext listens for this to log the
// user out immediately, from wherever in the app the failing request fired.
export const UNAUTHORIZED_EVENT = "leetcoach:unauthorized";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, {
    headers,
    ...options,
  });

  if (res.status === 401) {
    clearToken();
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    throw new Error("401 Unauthorized");
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }

  // Any successful mutation may have changed data other pages/components
  // are displaying -- notify globally rather than relying on each caller
  // to remember to refresh things itself. Safe to call even if the
  // component that started this request has since unmounted (e.g. a long
  // sync call outliving a navigation away from Settings): whichever page
  // is mounted when this resolves picks it up via useDataVersion().
  const method = (options?.method || "GET").toUpperCase();
  if (method !== "GET") notifyDataChanged();

  if (res.status === 204) return undefined as T;
  return res.json();
}

// Login uses OAuth2's form-encoded convention (fields literally named
// "username"/"password") rather than our usual JSON body -- that's a
// FastAPI/OAuth2 convention on the backend, not something we chose here.
// It also can't reuse request() as-is: it runs before we have a token, and
// a failed login should surface as a normal rejected call, not a global
// logout event.
async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  const data: TokenResponse = await res.json();
  setToken(data.access_token);
  return data;
}

async function signup(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${BASE}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  const data: TokenResponse = await res.json();
  setToken(data.access_token);
  return data;
}

export interface ProblemFilters {
  search?: string;
  difficulty?: string;
  topic?: string;
  solved?: boolean;
  bookmarked?: boolean;
  needs_revision?: boolean;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}

function buildQuery(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") usp.set(k, String(v));
  }
  const qs = usp.toString();
  return qs ? `?${qs}` : "";
}

export const api = {
  login,
  signup,
  getMe: () => request<AuthUser>(`/api/auth/me`),

  loadSampleProblems: () => request<{ added: number }>(`/api/problems/load-sample`, { method: "POST" }),

  getProblems: (filters: ProblemFilters = {}) =>
    request<Problem[]>(`/api/problems${buildQuery(filters as Record<string, unknown>)}`),
  getProblem: (id: number) => request<Problem>(`/api/problems/${id}`),
  getTopicsList: () => request<string[]>(`/api/problems/topics`),
  updateProblem: (id: number, data: Partial<Problem>) =>
    request<Problem>(`/api/problems/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  upsertNote: (id: number, note: Partial<Note>) =>
    request<Note>(`/api/problems/${id}/note`, { method: "PUT", body: JSON.stringify(note) }),

  getDashboard: () => request<DashboardStats>(`/api/dashboard`),

  getHistory: () => request<SolveLogEntry[]>(`/api/history`),
  getCalendar: (days = 84) => request<Record<string, number>>(`/api/history/calendar?days=${days}`),

  getRevisionDue: () => request<Problem[]>(`/api/revision/due`),
  getAllRevisions: () => request<Problem[]>(`/api/revision`),
  markForRevision: (id: number) => request<Problem>(`/api/revision/${id}/mark`, { method: "POST" }),
  unmarkRevision: (id: number) => request<Problem>(`/api/revision/${id}/unmark`, { method: "POST" }),
  completeRevision: (id: number, confidence?: number) =>
    request<Problem>(`/api/revision/${id}/complete`, {
      method: "POST",
      body: JSON.stringify({ confidence: confidence ?? null }),
    }),

  getRecommendations: () => request<RecommendationResponse>(`/api/recommendations`),

  getTopicStats: () => request<TopicStat[]>(`/api/topics`),
  getTopicTrends: (days = 14) => request<Record<string, number>>(`/api/topics/trends?days=${days}`),

  getSettings: () => request<UserSettings>(`/api/settings`),
  updateSettings: (data: Partial<UserSettings>) =>
    request<UserSettings>(`/api/settings`, { method: "PATCH", body: JSON.stringify(data) }),
  getSyncAvailability: () => request<{ available: boolean }>(`/api/settings/sync-status`),

  syncLeetCode: (username?: string) =>
    request<SyncStatus>(`/api/sync/leetcode`, {
      method: "POST",
      body: JSON.stringify({ username: username || null }),
    }),
  getSyncStatus: () => request<SyncStatus>(`/api/sync/status`),
};
