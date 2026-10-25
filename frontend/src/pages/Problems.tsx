import { useEffect, useState, useCallback } from "react";
import { api } from "../api/client";
import { useDataVersion } from "../api/useDataVersion";
import type { Problem } from "../api/types";
import { ProblemsTable } from "../components/ProblemsTable";

type SolvedFilter = "all" | "solved" | "unsolved";

export function Problems() {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [topic, setTopic] = useState("");
  const [solvedFilter, setSolvedFilter] = useState<SolvedFilter>("all");
  const [bookmarkedOnly, setBookmarkedOnly] = useState(false);
  const [revisionOnly, setRevisionOnly] = useState(false);
  const [sortBy, setSortBy] = useState("leetcode_id");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const version = useDataVersion();

  useEffect(() => {
    api.getTopicsList().then(setTopics);
  }, [version]);

  const load = useCallback(() => {
    setLoading(true);
    api
      .getProblems({
        search: search || undefined,
        difficulty: difficulty || undefined,
        topic: topic || undefined,
        solved: solvedFilter === "all" ? undefined : solvedFilter === "solved",
        bookmarked: bookmarkedOnly ? true : undefined,
        needs_revision: revisionOnly ? true : undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
      })
      .then((data) => {
        setProblems(data);
        setLoading(false);
      });
  }, [search, difficulty, topic, solvedFilter, bookmarkedOnly, revisionOnly, sortBy, sortDir, version]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  return (
    <div>
      <h1 className="page-title">Problems</h1>
      <p className="page-subtitle">{problems.length} problem(s) match your filters.</p>

      <div className="filter-bar">
        <input
          placeholder="Search title or #..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ minWidth: 220 }}
        />
        <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
          <option value="">All Difficulties</option>
          <option value="Easy">Easy</option>
          <option value="Medium">Medium</option>
          <option value="Hard">Hard</option>
        </select>
        <select value={topic} onChange={(e) => setTopic(e.target.value)}>
          <option value="">All Topics</option>
          {topics.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <div className="pill-toggle">
          {(["all", "solved", "unsolved"] as SolvedFilter[]).map((f) => (
            <button key={f} className={solvedFilter === f ? "active" : ""} onClick={() => setSolvedFilter(f)}>
              {f === "all" ? "All" : f === "solved" ? "Solved" : "Unsolved"}
            </button>
          ))}
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 0 }}>
          <input type="checkbox" checked={bookmarkedOnly} onChange={(e) => setBookmarkedOnly(e.target.checked)} />
          Bookmarked
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 0 }}>
          <input type="checkbox" checked={revisionOnly} onChange={(e) => setRevisionOnly(e.target.checked)} />
          Needs Revision
        </label>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="leetcode_id">Sort: # </option>
          <option value="title">Sort: Title</option>
          <option value="difficulty">Sort: Difficulty</option>
          <option value="date_solved">Sort: Date Solved</option>
          <option value="confidence">Sort: Confidence</option>
        </select>
        <button className="btn btn-sm" onClick={() => setSortDir((d) => (d === "asc" ? "desc" : "asc"))}>
          {sortDir === "asc" ? "↑ Asc" : "↓ Desc"}
        </button>
      </div>

      <div className="card">
        {loading ? <div className="empty-state">Loading…</div> : <ProblemsTable problems={problems} showDate />}
      </div>
    </div>
  );
}
