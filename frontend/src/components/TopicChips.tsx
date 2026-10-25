export function TopicChips({ topics }: { topics: string[] }) {
  return (
    <span>
      {topics.map((t) => (
        <span key={t} className="topic-chip">
          {t}
        </span>
      ))}
    </span>
  );
}
