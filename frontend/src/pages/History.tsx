import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useDataVersion } from "../api/useDataVersion";
import type { SolveLogEntry } from "../api/types";
import { DifficultyBadge } from "../components/DifficultyBadge";
import { TopicChips } from "../components/TopicChips";

function heatColor(count: number): string {
  if (count === 0) return "var(--bg-elevated)";
  if (count === 1) return "rgba(109,139,255,0.35)";
  if (count === 2) return "rgba(109,139,255,0.6)";
  return "rgba(109,139,255,0.9)";
}

export function History() {
  const [logs, setLogs] = useState<SolveLogEntry[]>([]);
  const [calendar, setCalendar] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const version = useDataVersion();

  useEffect(() => {
    Promise.all([api.getHistory(), api.getCalendar(84)]).then(([h, c]) => {
      setLogs(h);
      setCalendar(c);
      setLoading(false);
    });
  }, [version]);

  if (loading) return <div className="empty-state">Loading…</div>;

  const days: string[] = [];
  const start = new Date();
  start.setDate(start.getDate() - 83);
  for (let i = 0; i < 84; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    days.push(d.toISOString().slice(0, 10));
  }

  return (
    <div>
      <h1 className="page-title">Solving History</h1>
      <p className="page-subtitle">Chronological record of every problem solved and revised.</p>

      <div className="card">
        <h3>Activity (last 12 weeks)</h3>
        <div className="calendar-grid">
          {days.map((day) => (
            <div
              key={day}
              className="calendar-cell"
              title={`${day}: ${calendar[day] ?? 0} solve(s)`}
              style={{ background: heatColor(calendar[day] ?? 0) }}
            />
          ))}
        </div>
      </div>

      <div className="section-heading">
        <h2>Timeline ({logs.length} entries)</h2>
      </div>
      <div className="card">
        {logs.length === 0 ? (
          <div className="empty-state">No history yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Problem</th>
                <th>Difficulty</th>
                <th>Type</th>
                <th>Topics</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td>{log.date}</td>
                  <td>
                    {log.problem.leetcode_id}. {log.problem.title}
                  </td>
                  <td>
                    <DifficultyBadge difficulty={log.problem.difficulty} />
                  </td>
                  <td>
                    <span className={`badge ${log.type === "new" ? "badge-strong" : "badge-low_coverage"}`}>
                      {log.type === "new" ? "New" : "Revision"}
                    </span>
                  </td>
                  <td>
                    <TopicChips topics={log.problem.topics} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
