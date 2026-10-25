export function ConfidenceStars({
  value,
  onChange,
}: {
  value: number | null;
  onChange?: (v: number) => void;
}) {
  const stars = [1, 2, 3, 4, 5];
  return (
    <span className="star-row">
      {stars.map((s) => (
        <span
          key={s}
          onClick={() => onChange?.(s)}
          style={{
            cursor: onChange ? "pointer" : "default",
            color: value !== null && s <= value ? "var(--medium)" : "var(--border)",
            fontSize: 14,
          }}
        >
          ★
        </span>
      ))}
    </span>
  );
}
