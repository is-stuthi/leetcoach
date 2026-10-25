import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { UserSettings, SyncStatus } from "../api/types";

const ALL_TOPICS_FALLBACK = [
  "Array", "Hash Table", "Two Pointers", "Sliding Window", "Linked List",
  "Binary Search", "Trees", "Graphs", "Heap / Priority Queue", "Dynamic Programming",
];

export function Settings() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [topics, setTopics] = useState<string[]>(ALL_TOPICS_FALLBACK);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([api.getSettings(), api.getTopicsList(), api.getSyncStatus()]).then(
      ([s, t, status]) => {
        setSettings(s);
        setTopics(t.length ? t : ALL_TOPICS_FALLBACK);
        setSyncStatus(status);
      }
    );
  }, []);

  const runSync = async () => {
    if (!settings?.leetcode_username) return;
    setSyncing(true);
    setSyncError(null);
    try {
      // persist the username first so it's saved even if sync then fails
      await api.updateSettings({ leetcode_username: settings.leetcode_username });
      const status = await api.syncLeetCode(settings.leetcode_username);
      setSyncStatus(status);
      const refreshedTopics = await api.getTopicsList();
      setTopics(refreshedTopics.length ? refreshedTopics : ALL_TOPICS_FALLBACK);
    } catch (e) {
      setSyncError(e instanceof Error ? e.message : String(e));
      const status = await api.getSyncStatus();
      setSyncStatus(status);
    } finally {
      setSyncing(false);
    }
  };

  if (!settings) return <div className="empty-state">Loading…</div>;

  const update = <K extends keyof UserSettings>(key: K, value: UserSettings[K]) => {
    setSettings({ ...settings, [key]: value });
  };

  const toggleTopic = (topic: string) => {
    const set = new Set(settings.priority_topics);
    if (set.has(topic)) set.delete(topic);
    else set.add(topic);
    update("priority_topics", Array.from(set));
  };

  const save = async () => {
    setSaving(true);
    const updated = await api.updateSettings(settings);
    setSettings(updated);
    setSaving(false);
    setSavedAt(Date.now());
  };

  const setInterval = (index: number, value: number) => {
    const next = [...settings.revision_intervals];
    next[index] = value;
    update("revision_intervals", next);
  };

  return (
    <div>
      <h1 className="page-title">Settings</h1>
      <p className="page-subtitle">Configure daily targets, priorities, and revision behavior.</p>

      <div className="card" style={{ marginBottom: 20 }}>
        <h3>LeetCode Sync</h3>
        <label>LeetCode Username</label>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <input
            value={settings.leetcode_username}
            onChange={(e) => update("leetcode_username", e.target.value)}
            placeholder="your-leetcode-username"
            style={{ maxWidth: 320 }}
          />
          <button
            className="btn btn-primary btn-sm"
            onClick={runSync}
            disabled={syncing || !settings.leetcode_username}
          >
            {syncing ? "Syncing…" : "Sync LeetCode"}
          </button>
        </div>
        <p className="stat-sub" style={{ marginTop: 10 }}>
          Pulls your public solved-problem stats and recent solves from LeetCode's public profile
          API — no password or session cookie is ever required or requested. Because that public API only
          exposes your ~20 most recent accepted submissions (LeetCode doesn't expose full history without
          login), a sync also refreshes LeetCoach's practice-problem catalog from LeetCode's real problem
          set so recommendations always have a real pool to draw from.
        </p>

        {syncError && (
          <p className="stat-sub" style={{ color: "var(--hard)", marginTop: 8 }}>
            Sync failed: {syncError}
          </p>
        )}

        {syncStatus && (syncStatus.last_synced_at || syncStatus.errors.length > 0) && (
          <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
            <div className="grid grid-3" style={{ marginBottom: 10 }}>
              <div>
                <span className="stat-label">Last Synced</span>
                <div>
                  {syncStatus.last_synced_at
                    ? new Date(syncStatus.last_synced_at + "Z").toLocaleString()
                    : "Never"}
                  {syncStatus.success ? (
                    <span className="badge badge-strong" style={{ marginLeft: 8 }}>OK</span>
                  ) : (
                    <span className="badge badge-weak" style={{ marginLeft: 8 }}>Failed</span>
                  )}
                </div>
              </div>
              <div>
                <span className="stat-label">Catalog Problems Synced</span>
                <div>{syncStatus.problems_synced}</div>
              </div>
              <div>
                <span className="stat-label">Newly Marked Solved</span>
                <div>{syncStatus.newly_solved}</div>
              </div>
            </div>

            {syncStatus.reported_total !== null && (
              <p className="stat-sub" style={{ marginBottom: 10 }}>
                LeetCode reports <strong>{syncStatus.reported_total}</strong> total solved
                ({syncStatus.reported_easy} Easy / {syncStatus.reported_medium} Medium /{" "}
                {syncStatus.reported_hard} Hard) for {syncStatus.username_synced}. LeetCoach can only
                individually track solves it can see through the public API, shown above.
              </p>
            )}

            {syncStatus.errors.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                {syncStatus.errors.map((e, i) => (
                  <div key={i} className="stat-sub" style={{ color: "var(--hard)" }}>
                    ⚠ {e}
                  </div>
                ))}
              </div>
            )}
            {syncStatus.warnings.length > 0 && (
              <div>
                {syncStatus.warnings.map((w, i) => (
                  <div key={i} className="stat-sub" style={{ color: "var(--medium)" }}>
                    • {w}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h3>Daily Targets</h3>
          <div style={{ marginBottom: 14 }}>
            <label>New problems per day</label>
            <input
              type="number"
              min={0}
              max={10}
              value={settings.daily_target_new}
              onChange={(e) => update("daily_target_new", Number(e.target.value))}
              style={{ width: 100 }}
            />
          </div>
          <div>
            <label>Revision problems per day</label>
            <input
              type="number"
              min={0}
              max={10}
              value={settings.daily_target_revision}
              onChange={(e) => update("daily_target_revision", Number(e.target.value))}
              style={{ width: 100 }}
            />
          </div>
        </div>

        <div className="card">
          <h3>Preferred Difficulty</h3>
          <select
            value={settings.preferred_difficulty}
            onChange={(e) => update("preferred_difficulty", e.target.value as UserSettings["preferred_difficulty"])}
          >
            <option value="Easy">Easy</option>
            <option value="Medium">Medium</option>
            <option value="Hard">Hard</option>
          </select>
          <p className="stat-sub" style={{ marginTop: 10 }}>
            Used by the recommendation engine to weight candidate problems.
          </p>
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <h3>Priority Topics</h3>
        <p className="stat-sub" style={{ marginTop: -4, marginBottom: 12 }}>
          Problems in these topics get a scoring boost in recommendations.
        </p>
        <div>
          {topics.map((t) => (
            <span
              key={t}
              onClick={() => toggleTopic(t)}
              className="topic-chip"
              style={{
                cursor: "pointer",
                padding: "5px 12px",
                fontSize: 12,
                background: settings.priority_topics.includes(t) ? "var(--accent-soft)" : undefined,
                color: settings.priority_topics.includes(t) ? "var(--accent)" : undefined,
                borderColor: settings.priority_topics.includes(t) ? "var(--accent)" : undefined,
              }}
            >
              {t}
            </span>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <h3>Revision Intervals (days)</h3>
        <p className="stat-sub" style={{ marginTop: -4, marginBottom: 12 }}>
          Default spaced-repetition ladder: 3 → 10 → 30 days. A struggled problem (low confidence) resets to
          the first interval instead of advancing.
        </p>
        <div className="btn-row">
          {settings.revision_intervals.map((interval, i) => (
            <div key={i}>
              <label>Stage {i + 1}</label>
              <input
                type="number"
                min={1}
                value={interval}
                onChange={(e) => setInterval(i, Number(e.target.value))}
                style={{ width: 90 }}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="btn-row" style={{ marginTop: 20 }}>
        <button className="btn btn-primary" onClick={save} disabled={saving}>
          {saving ? "Saving…" : "Save Settings"}
        </button>
        {savedAt && <span className="stat-sub" style={{ alignSelf: "center" }}>Saved ✓</span>}
      </div>
    </div>
  );
}
