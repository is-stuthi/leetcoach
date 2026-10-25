import { useNavigate } from "react-router-dom";
import type { Problem } from "../api/types";
import { DifficultyBadge } from "./DifficultyBadge";
import { TopicChips } from "./TopicChips";

export function ProblemsTable({
  problems,
  showDate = false,
  emptyMessage = "No problems found.",
}: {
  problems: Problem[];
  showDate?: boolean;
  emptyMessage?: string;
}) {
  const navigate = useNavigate();

  if (problems.length === 0) {
    return <div className="empty-state">{emptyMessage}</div>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Title</th>
          <th>Difficulty</th>
          <th>Topics</th>
          <th>Status</th>
          {showDate && <th>Date Solved</th>}
          <th></th>
        </tr>
      </thead>
      <tbody>
        {problems.map((p) => (
          <tr key={p.id} className="clickable" onClick={() => navigate(`/notebook/${p.id}`)}>
            <td>{p.leetcode_id}</td>
            <td>
              {p.title} {p.bookmarked && <span title="Bookmarked">🔖</span>}
            </td>
            <td>
              <DifficultyBadge difficulty={p.difficulty} />
            </td>
            <td>
              <TopicChips topics={p.topics} />
            </td>
            <td>
              {p.solved ? (
                <span className="badge badge-strong">Solved</span>
              ) : (
                <span className="badge badge-neutral">Unsolved</span>
              )}
              {p.needs_revision && <span className="badge badge-low_coverage" style={{ marginLeft: 6 }}>Revision</span>}
            </td>
            {showDate && <td>{p.date_solved ?? "—"}</td>}
            <td>
              <a
                href={p.url}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
              >
                LeetCode ↗
              </a>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
