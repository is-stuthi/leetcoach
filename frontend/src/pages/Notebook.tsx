import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useDataVersion } from "../api/useDataVersion";
import type { Problem } from "../api/types";
import { DifficultyBadge } from "../components/DifficultyBadge";
import { TopicChips } from "../components/TopicChips";
import { ConfidenceStars } from "../components/ConfidenceStars";

export function Notebook() {
  const { problemId } = useParams();
  const navigate = useNavigate();
  const [problems, setProblems] = useState<Problem[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Problem | null>(null);
  const [loading, setLoading] = useState(true);
  const version = useDataVersion();

  useEffect(() => {
    api.getProblems({ sort_by: "leetcode_id" }).then((data) => {
      setProblems(data);
      setLoading(false);
    });
  }, [version]);

  useEffect(() => {
    if (!problemId || problems.length === 0) return;
    const p = problems.find((pr) => pr.id === Number(problemId));
    if (p) setSelected(p);
  }, [problemId, problems]);

  const filtered = problems.filter(
    (p) => p.title.toLowerCase().includes(search.toLowerCase()) || String(p.leetcode_id).includes(search)
  );

  const selectProblem = (p: Problem) => {
    setSelected(p);
    navigate(`/notebook/${p.id}`, { replace: true });
  };

  if (loading) return <div className="empty-state">Loading…</div>;

  return (
    <div>
      <h1 className="page-title">Notebook</h1>
      <p className="page-subtitle">Personal notes, insights, mistakes, and complexity tracking per problem.</p>

      <div className="two-col">
        <div className="card" style={{ maxHeight: 640, overflowY: "auto" }}>
          <input
            placeholder="Search problems…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: "100%", marginBottom: 12 }}
          />
          {filtered.map((p) => (
            <div
              key={p.id}
              onClick={() => selectProblem(p)}
              style={{
                padding: "10px 8px",
                borderRadius: 8,
                cursor: "pointer",
                background: selected?.id === p.id ? "var(--accent-soft)" : "transparent",
                marginBottom: 2,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>
                  {p.leetcode_id}. {p.title}
                </span>
                {p.note?.notes_text && <span title="Has notes">📝</span>}
              </div>
              <div style={{ marginTop: 4 }}>
                <DifficultyBadge difficulty={p.difficulty} />
                {!p.solved && <span className="badge badge-neutral" style={{ marginLeft: 6 }}>Unsolved</span>}
              </div>
            </div>
          ))}
          {filtered.length === 0 && <div className="empty-state">No matches.</div>}
        </div>

        <div>
          {selected ? (
            <NoteEditor
              key={selected.id}
              problem={selected}
              onUpdated={(p) => {
                setSelected(p);
                setProblems((prev) => prev.map((x) => (x.id === p.id ? p : x)));
              }}
            />
          ) : (
            <div className="card empty-state">Select a problem from the list to view or edit notes.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function NoteEditor({ problem, onUpdated }: { problem: Problem; onUpdated: (p: Problem) => void }) {
  const [notesText, setNotesText] = useState(problem.note?.notes_text ?? "");
  const [keyInsight, setKeyInsight] = useState(problem.note?.key_insight ?? "");
  const [mistake, setMistake] = useState(problem.note?.mistake ?? "");
  const [timeComplexity, setTimeComplexity] = useState(problem.note?.time_complexity ?? "");
  const [spaceComplexity, setSpaceComplexity] = useState(problem.note?.space_complexity ?? "");
  const [confidence, setConfidence] = useState<number | null>(problem.confidence);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const save = async () => {
    setSaving(true);
    await api.upsertNote(problem.id, {
      notes_text: notesText,
      key_insight: keyInsight,
      mistake,
      time_complexity: timeComplexity,
      space_complexity: spaceComplexity,
    });
    const updated = await api.updateProblem(problem.id, { confidence: confidence ?? undefined });
    setSaving(false);
    setSavedAt(Date.now());
    onUpdated(updated);
  };

  const toggleBookmark = async () => {
    const updated = await api.updateProblem(problem.id, { bookmarked: !problem.bookmarked });
    onUpdated(updated);
  };

  const toggleRevision = async () => {
    const updated = problem.needs_revision ? await api.unmarkRevision(problem.id) : await api.markForRevision(problem.id);
    onUpdated(updated);
  };

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h3>
            {problem.leetcode_id}. {problem.title}
          </h3>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
            <DifficultyBadge difficulty={problem.difficulty} />
            <TopicChips topics={problem.topics} />
          </div>
        </div>
        <a href={problem.url} target="_blank" rel="noreferrer" className="btn btn-sm">
          LeetCode ↗
        </a>
      </div>

      <div className="btn-row" style={{ margin: "12px 0" }}>
        <button className="btn btn-sm" onClick={toggleBookmark}>
          {problem.bookmarked ? "🔖 Bookmarked" : "🔖 Bookmark"}
        </button>
        {problem.solved && (
          <button className="btn btn-sm" onClick={toggleRevision}>
            {problem.needs_revision ? "🔁 Scheduled for revision" : "🔁 Mark for revision"}
          </button>
        )}
        {!problem.solved && (
          <button
            className="btn btn-sm"
            onClick={async () => {
              const updated = await api.updateProblem(problem.id, {
                solved: true,
                date_solved: new Date().toISOString().slice(0, 10),
              });
              onUpdated(updated);
            }}
          >
            ✓ Mark as solved
          </button>
        )}
      </div>

      <div style={{ marginBottom: 14 }}>
        <label>Confidence</label>
        <ConfidenceStars value={confidence} onChange={setConfidence} />
      </div>

      <div className="grid grid-2">
        <div>
          <label>Time Complexity</label>
          <input value={timeComplexity} onChange={(e) => setTimeComplexity(e.target.value)} placeholder="e.g. O(n log n)" />
        </div>
        <div>
          <label>Space Complexity</label>
          <input value={spaceComplexity} onChange={(e) => setSpaceComplexity(e.target.value)} placeholder="e.g. O(n)" />
        </div>
      </div>

      <div style={{ marginTop: 14 }}>
        <label>Personal Notes</label>
        <textarea rows={4} value={notesText} onChange={(e) => setNotesText(e.target.value)} placeholder="Approach, edge cases, general notes…" />
      </div>

      <div style={{ marginTop: 14 }}>
        <label>Key Insight</label>
        <textarea rows={2} value={keyInsight} onChange={(e) => setKeyInsight(e.target.value)} placeholder="The 'aha' that unlocked this problem…" />
      </div>

      <div style={{ marginTop: 14 }}>
        <label>Mistake Made</label>
        <textarea rows={2} value={mistake} onChange={(e) => setMistake(e.target.value)} placeholder="What tripped you up, if anything…" />
      </div>

      <div className="btn-row" style={{ marginTop: 16 }}>
        <button className="btn btn-primary" onClick={save} disabled={saving}>
          {saving ? "Saving…" : "Save Notes"}
        </button>
        {savedAt && <span className="stat-sub" style={{ alignSelf: "center" }}>Saved ✓</span>}
      </div>
    </div>
  );
}
