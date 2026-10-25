import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useDataVersion } from "../api/useDataVersion";
import type { Problem } from "../api/types";
import { DifficultyBadge } from "../components/DifficultyBadge";
import { TopicChips } from "../components/TopicChips";
import { ConfidenceStars } from "../components/ConfidenceStars";

export function Revision() {
  const [due, setDue] = useState<Problem[]>([]);
  const [all, setAll] = useState<Problem[]>([]);
  const [solvedNotFlagged, setSolvedNotFlagged] = useState<Problem[]>([]);
  const [loading, setLoading] = useState(true);
  const version = useDataVersion();

  const reload = () => {
    Promise.all([api.getRevisionDue(), api.getAllRevisions(), api.getProblems({ solved: true })]).then(
      ([dueList, allList, solved]) => {
        setDue(dueList);
        setAll(allList);
        setSolvedNotFlagged(solved.filter((p) => !p.needs_revision));
        setLoading(false);
      }
    );
  };

  useEffect(reload, [version]);

  if (loading) return <div className="empty-state">Loading…</div>;

  const upcoming = all.filter((p) => !due.some((d) => d.id === p.id));

  return (
    <div>
      <h1 className="page-title">Revision</h1>
      <p className="page-subtitle">
        Spaced repetition: default intervals are 3 → 10 → 30 days. Struggled problems (low confidence) get
        revisited sooner instead of advancing to the next interval.
      </p>

      <div className="section-heading">
        <h2>Due Today ({due.length})</h2>
      </div>
      <div className="card">
        {due.length === 0 ? (
          <div className="empty-state">Nothing due today. Nice work.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Title</th>
                <th>Difficulty</th>
                <th>Topics</th>
                <th>Confidence</th>
                <th>Revisions Done</th>
                <th>Complete Revision</th>
              </tr>
            </thead>
            <tbody>
              {due.map((p) => (
                <RevisionRow key={p.id} problem={p} onDone={reload} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="section-heading">
        <h2>Upcoming Revisions ({upcoming.length})</h2>
      </div>
      <div className="card">
        {upcoming.length === 0 ? (
          <div className="empty-state">Nothing scheduled beyond today.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Title</th>
                <th>Next Revision</th>
                <th>Revisions Done</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {upcoming.map((p) => (
                <tr key={p.id}>
                  <td>{p.leetcode_id}</td>
                  <td>{p.title}</td>
                  <td>{p.revision?.next_revision_date ?? "—"}</td>
                  <td>{p.revision?.revision_count ?? 0}</td>
                  <td>
                    <button
                      className="btn btn-sm"
                      onClick={() => api.unmarkRevision(p.id).then(reload)}
                    >
                      Remove from revision
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="section-heading">
        <h2>Mark a Solved Problem for Revision</h2>
      </div>
      <div className="card">
        {solvedNotFlagged.length === 0 ? (
          <div className="empty-state">All solved problems are already scheduled or none solved yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Title</th>
                <th>Difficulty</th>
                <th>Topics</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {solvedNotFlagged.map((p) => (
                <tr key={p.id}>
                  <td>{p.leetcode_id}</td>
                  <td>{p.title}</td>
                  <td>
                    <DifficultyBadge difficulty={p.difficulty} />
                  </td>
                  <td>
                    <TopicChips topics={p.topics} />
                  </td>
                  <td>
                    <button className="btn btn-sm btn-primary" onClick={() => api.markForRevision(p.id).then(reload)}>
                      Schedule revision
                    </button>
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

function RevisionRow({ problem, onDone }: { problem: Problem; onDone: () => void }) {
  const [confidence, setConfidence] = useState<number>(problem.confidence ?? 3);
  const [busy, setBusy] = useState(false);

  const complete = async () => {
    setBusy(true);
    await api.completeRevision(problem.id, confidence);
    setBusy(false);
    onDone();
  };

  return (
    <tr>
      <td>{problem.leetcode_id}</td>
      <td>{problem.title}</td>
      <td>
        <DifficultyBadge difficulty={problem.difficulty} />
      </td>
      <td>
        <TopicChips topics={problem.topics} />
      </td>
      <td>
        <ConfidenceStars value={confidence} onChange={setConfidence} />
      </td>
      <td>{problem.revision?.revision_count ?? 0}</td>
      <td>
        <button className="btn btn-sm btn-primary" disabled={busy} onClick={complete}>
          {busy ? "Saving…" : "Mark revised"}
        </button>
      </td>
    </tr>
  );
}
