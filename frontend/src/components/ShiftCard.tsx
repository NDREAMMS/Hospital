import type { Shift } from "../types";

export function ShiftCard({
  shift,
  selected,
  onClick,
}: {
  shift: Shift;
  selected?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      className="card"
      onClick={onClick}
      style={{
        textAlign: "left",
        cursor: onClick ? "pointer" : "default",
        outline: "none",
        borderColor: selected ? "rgba(99,102,241,0.8)" : undefined,
        boxShadow: selected ? "0 0 0 3px rgba(99,102,241,0.18)" : undefined,
      }}
    >
      <div style={{ fontWeight: 600 }}>{shift.title}</div>
      <div className="muted" style={{ fontSize: 13 }}>
        {shift.start} → {shift.end}
      </div>
    </button>
  );
}
