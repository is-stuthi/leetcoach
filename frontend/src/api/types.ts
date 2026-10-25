export type Difficulty = "Easy" | "Medium" | "Hard";

export interface AuthUser {
  id: number;
  email: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface Note {
  id: number;
  problem_id: number;
  notes_text: string;
  key_insight: string;
  mistake: string;
  time_complexity: string;
  space_complexity: string;
  updated_at: string;
}

export interface RevisionInfo {
  id: number;
  problem_id: number;
  revision_count: number;
  interval_stage: number;
  last_revised_at: string | null;
  next_revision_date: string | null;
  active: boolean;
}

export interface Problem {
  id: number;
  leetcode_id: number;
  title: string;
  difficulty: Difficulty;
  topics: string[];
  url: string;
  solved: boolean;
  date_solved: string | null;
  bookmarked: boolean;
  confidence: number | null;
  needs_revision: boolean;
  source: "seed" | "synced";
  note: Note | null;
  revision: RevisionInfo | null;
}

export interface DifficultyCounts {
  Easy: number;
  Medium: number;
  Hard: number;
}

export interface DashboardStats {
  total_solved: number;
  total_problems: number;
  difficulty_counts: DifficultyCounts;
  solved_this_week: number;
  current_streak: number;
  topic_distribution: Record<string, number>;
  activity_over_time: Record<string, number>;
  revisions_due_today: Problem[];
  bookmarked: Problem[];
  recent_problems: Problem[];
}

export interface RecommendationItem {
  problem: Problem;
  kind: "new" | "revision" | "extra";
  score: number;
  reasons: string[];
}

export interface RecommendationResponse {
  items: RecommendationItem[];
  insights: string[];
}

export interface TopicStat {
  topic: string;
  solved: number;
  total: number;
  coverage: number;
  avg_confidence: number | null;
  label: "strong" | "weak" | "low_coverage" | "neutral";
  reason: string;
}

export interface SolveLogEntry {
  id: number;
  problem_id: number;
  date: string;
  type: "new" | "revision";
  problem: Problem;
}

export interface UserSettings {
  id: number;
  leetcode_username: string;
  daily_target_new: number;
  daily_target_revision: number;
  preferred_difficulty: Difficulty;
  priority_topics: string[];
  revision_intervals: number[];
}

export interface SyncStatus {
  username_synced: string | null;
  last_synced_at: string | null;
  success: boolean;
  problems_synced: number;
  newly_solved: number;
  warnings: string[];
  errors: string[];
  reported_easy: number | null;
  reported_medium: number | null;
  reported_hard: number | null;
  reported_total: number | null;
}
