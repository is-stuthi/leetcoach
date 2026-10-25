import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useDataVersion } from "../api/useDataVersion";
import type { RecommendationItem, TopicStat } from "../api/types";
import { DifficultyBadge } from "../components/DifficultyBadge";
import { TopicChips } from "../components/TopicChips";

const KIND_LABEL: Record<string, string> = {
  new: "New Problem",
  revision: "Revision Due",
  extra: "Extra Practice",
};

export function Recommendations() {
  const [items, setItems] = useState<RecommendationItem[]>([]);
  const [insights, setInsights] = useState<string[]>([]);
  const [topics, setTopics] = useState<TopicStat[]>([]);
  const [loading, setLoading] = useState(true);
  const version = useDataVersion();

  useEffect(() => {
    Promise.all([api.getRecommendations(), api.getTopicStats()]).then(([recs, topicStats]) => {
      setItems(recs.items);
      setInsights(recs.insights);
      setTopics(topicStats);
      setLoading(false);
    });
  }, [version]);

  if (loading) return <div className="empty-state">Loading…</div>;

  const strong = topics.filter((t) => t.label === "strong");
  const weak = topics.filter((t) => t.label === "weak");
  const lowCoverage = topics.filter((t) => t.label === "low_coverage");

  return (
    <div>
      <h1 className="page-title">Recommendations</h1>
      <p className="page-subtitle">
        Transparent, rule-based picks — no ML, no LLM. Every recommendation shows exactly why it was chosen.
      </p>

      {insights.length > 0 && (
        <div className="card" style={{ marginBottom: 20, borderColor: "var(--medium)" }}>
          {insights.map((insight, i) => (
            <div key={i} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
              <span style={{ color: "var(--medium)" }}>⚠</span>
              <span className="stat-sub" style={{ color: "var(--text)" }}>{insight}</span>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-3">
        {items.length === 0 && <div className="empty-state">No recommendations available right now.</div>}
        {items.map((item) => (
          <div key={`${item.kind}-${item.problem.id}`} className="rec-card">
            <span className={`rec-kind rec-kind-${item.kind}`}>{KIND_LABEL[item.kind]}</span>
            <strong style={{ fontSize: 15 }}>
              {item.problem.leetcode_id}. {item.problem.title}
            </strong>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <DifficultyBadge difficulty={item.problem.difficulty} />
              <TopicChips topics={item.problem.topics} />
            </div>
            <span className="stat-sub">Score: {item.score.toFixed(0)} · Recommended because:</span>
            <ul className="reason-list">
              {item.reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
            <a
              href={item.problem.url}
              target="_blank"
              rel="noreferrer"
              className="btn btn-sm btn-primary"
              style={{ alignSelf: "flex-start", marginTop: "auto" }}
            >
              Open on LeetCode
            </a>
          </div>
        ))}
      </div>

      <div className="section-heading">
        <h2>Topic Analysis</h2>
      </div>
      <p className="page-subtitle" style={{ marginTop: -6 }}>
        A topic is only called "weak" when you've actually attempted it and rated your confidence low — never
        just because you've solved fewer of them.
      </p>

      <div className="grid grid-3">
        <TopicColumn title="Strongest Topics" topics={strong} color="var(--easy)" />
        <TopicColumn title="Needs Practice" topics={weak} color="var(--hard)" />
        <TopicColumn title="Low Coverage (not enough data)" topics={lowCoverage} color="var(--medium)" />
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <h3>All Topics</h3>
        <table>
          <thead>
            <tr>
              <th>Topic</th>
              <th>Coverage</th>
              <th>Avg Confidence</th>
              <th>Label</th>
              <th>Reasoning</th>
            </tr>
          </thead>
          <tbody>
            {topics.map((t) => (
              <tr key={t.topic}>
                <td>{t.topic}</td>
                <td>
                  {t.solved}/{t.total}
                  <div className="progress-bar" style={{ width: 80, marginTop: 4 }}>
                    <div
                      className="progress-fill"
                      style={{ width: `${t.coverage * 100}%`, background: "var(--accent)" }}
                    />
                  </div>
                </td>
                <td>{t.avg_confidence !== null ? `${t.avg_confidence.toFixed(1)}/5` : "—"}</td>
                <td>
                  <span className={`badge badge-${t.label}`}>{t.label.replace("_", " ")}</span>
                </td>
                <td className="stat-sub">{t.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TopicColumn({ title, topics, color }: { title: string; topics: TopicStat[]; color: string }) {
  return (
    <div className="card">
      <h3 style={{ color }}>{title}</h3>
      {topics.length === 0 ? (
        <div className="stat-sub">None yet.</div>
      ) : (
        topics.map((t) => (
          <div key={t.topic} style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
              <span>{t.topic}</span>
              <span className="stat-sub">
                {t.solved}/{t.total}
              </span>
            </div>
            <div className="stat-sub" style={{ fontSize: 11 }}>
              {t.reason}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
