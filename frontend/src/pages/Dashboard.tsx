import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  AreaChart, Area,
} from "recharts";
import { api } from "../api/client";
import { useDataVersion } from "../api/useDataVersion";
import type { DashboardStats } from "../api/types";
import { StatCard } from "../components/StatCard";
import { ProblemsTable } from "../components/ProblemsTable";

const DIFF_COLORS: Record<string, string> = {
  Easy: "#3ecf8e",
  Medium: "#f5a623",
  Hard: "#f0556b",
};

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const version = useDataVersion();

  useEffect(() => {
    api.getDashboard().then((s) => {
      setStats(s);
      setLoading(false);
    });
  }, [version]);

  if (loading || !stats) {
    return <div className="empty-state">Loading dashboard…</div>;
  }

  const diffData = Object.entries(stats.difficulty_counts)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }));

  const topicData = Object.entries(stats.topic_distribution)
    .sort((a, b) => b[1] - a[1])
    .map(([topic, count]) => ({ topic, count }));

  const activityData = Object.entries(stats.activity_over_time)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, count]) => ({ date: date.slice(5), count }));

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-subtitle">Your LeetCode training overview.</p>

      {stats.total_problems === 0 && <EmptyCatalogBanner />}

      <div className="grid grid-4">
        <StatCard
          label="Total Solved"
          value={`${stats.total_solved} / ${stats.total_problems}`}
          sub={
            stats.total_problems > 0
              ? `${Math.round((stats.total_solved / stats.total_problems) * 100)}% of tracked problems`
              : "Sync your LeetCode profile or ask about sample data in Settings"
          }
        />
        <StatCard
          label="Difficulty Split"
          value={`${stats.difficulty_counts.Easy}E / ${stats.difficulty_counts.Medium}M / ${stats.difficulty_counts.Hard}H`}
        />
        <StatCard label="Solved This Week" value={stats.solved_this_week} />
        <StatCard
          label="Current Streak"
          value={`${stats.current_streak} day${stats.current_streak === 1 ? "" : "s"}`}
          sub={stats.current_streak > 0 ? "keep it going 🔥" : "solve one today to start a streak"}
        />
      </div>

      <div className="section-heading">
        <h2>What should I solve today?</h2>
        <Link to="/recommendations" className="btn btn-sm">
          View all recommendations →
        </Link>
      </div>
      <RecommendationTeaser />

      <div className="two-col" style={{ marginTop: 32 }}>
        <div className="card">
          <h3>Solving Activity (last ~60 days)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={activityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2e3a" />
              <XAxis dataKey="date" stroke="#666c7d" fontSize={11} interval={4} />
              <YAxis stroke="#666c7d" fontSize={11} allowDecimals={false} />
              <Tooltip contentStyle={{ background: "#1b1e28", border: "1px solid #2a2e3a" }} />
              <Area type="monotone" dataKey="count" stroke="#6d8bff" fill="rgba(109,139,255,0.25)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3>Difficulty Distribution</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={diffData} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75} paddingAngle={2}>
                {diffData.map((entry) => (
                  <Cell key={entry.name} fill={DIFF_COLORS[entry.name]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: "#1b1e28", border: "1px solid #2a2e3a" }} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", justifyContent: "center", gap: 14, fontSize: 12 }}>
            {diffData.map((d) => (
              <span key={d.name} style={{ color: DIFF_COLORS[d.name] }}>
                ● {d.name} ({d.value})
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <h3>Topic Distribution</h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={topicData} layout="vertical" margin={{ left: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2e3a" horizontal={false} />
            <XAxis type="number" stroke="#666c7d" fontSize={11} allowDecimals={false} />
            <YAxis dataKey="topic" type="category" stroke="#9aa0b0" fontSize={11} width={140} />
            <Tooltip contentStyle={{ background: "#1b1e28", border: "1px solid #2a2e3a" }} />
            <Bar dataKey="count" fill="#6d8bff" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="section-heading">
        <h2>Revisions Due Today ({stats.revisions_due_today.length})</h2>
        <Link to="/revision" className="btn btn-sm">Go to Revision →</Link>
      </div>
      <div className="card">
        <ProblemsTable
          problems={stats.revisions_due_today}
          emptyMessage="Nothing due for revision today. Nice work."
        />
      </div>

      <div className="section-heading">
        <h2>Recent Problems</h2>
        <Link to="/history" className="btn btn-sm">View full history →</Link>
      </div>
      <div className="card">
        <ProblemsTable problems={stats.recent_problems} showDate emptyMessage="No solves yet." />
      </div>

      <div className="section-heading">
        <h2>Bookmarked ({stats.bookmarked.length})</h2>
      </div>
      <div className="card">
        <ProblemsTable problems={stats.bookmarked} emptyMessage="No bookmarks yet." />
      </div>
    </div>
  );
}

function EmptyCatalogBanner() {
  const [loading, setLoading] = useState(false);

  async function handleLoadSample() {
    setLoading(true);
    // request() already fires notifyDataChanged() on any non-GET call, and
    // this Dashboard already re-fetches on that signal via useDataVersion()
    // -- no manual reload needed, the existing data-refresh wiring handles it
    await api.loadSampleProblems();
    setLoading(false);
  }

  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <h3>No problems yet</h3>
      <p className="page-subtitle" style={{ margin: "4px 0 12px 0" }}>
        Load a ~40-problem starter catalog to try the app right now, or sync your
        real LeetCode profile in Settings if you already have one.
      </p>
      <div className="btn-row">
        <button className="btn btn-primary" onClick={handleLoadSample} disabled={loading}>
          {loading ? "Loading..." : "Load sample problems"}
        </button>
        <Link to="/settings" className="btn">Go to Settings to sync LeetCode →</Link>
      </div>
    </div>
  );
}

function RecommendationTeaser() {
  const [items, setItems] = useState<Awaited<ReturnType<typeof api.getRecommendations>>["items"]>([]);
  const [loading, setLoading] = useState(true);
  const version = useDataVersion();

  useEffect(() => {
    api.getRecommendations().then((r) => {
      setItems(r.items);
      setLoading(false);
    });
  }, [version]);

  if (loading) return <div className="empty-state">Loading recommendations…</div>;
  if (items.length === 0) return <div className="empty-state">No recommendations available right now.</div>;

  return (
    <div className="grid grid-3">
      {items.map((item) => (
        <div key={`${item.kind}-${item.problem.id}`} className="rec-card">
          <span className={`rec-kind rec-kind-${item.kind}`}>
            {item.kind === "new" ? "New Problem" : item.kind === "revision" ? "Revision Due" : "Extra Practice"}
          </span>
          <strong>
            {item.problem.leetcode_id}. {item.problem.title}
          </strong>
          <span className="stat-sub">Recommended because:</span>
          <ul className="reason-list">
            {item.reasons.slice(0, 3).map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
          <a href={item.problem.url} target="_blank" rel="noreferrer" className="btn btn-sm btn-primary" style={{ alignSelf: "flex-start" }}>
            Open on LeetCode
          </a>
        </div>
      ))}
    </div>
  );
}
