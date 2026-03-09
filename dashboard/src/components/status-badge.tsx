import type { BenchState } from "../types.ts";

const STATE_COLORS: Record<BenchState, string> = {
  idle: "green",
  flashing: "blue",
  testing: "blue",
  error: "red",
  offline: "grey",
  unknown: "grey",
};

interface StatusBadgeProps {
  state: string | null;
  healthy: boolean | null;
  stale: boolean;
}

export function StatusBadge({ state, healthy, stale }: StatusBadgeProps) {
  const displayState = state ?? "unknown";
  const color = STATE_COLORS[displayState as BenchState] ?? "grey";

  return (
    <span>
      <span
        style={{
          display: "inline-block",
          width: 10,
          height: 10,
          borderRadius: "50%",
          backgroundColor: color,
          marginRight: 6,
        }}
      />
      {displayState}
      {stale && (
        <small style={{ color: "orange", marginLeft: 6 }} title="Heartbeat stale">
          (stale)
        </small>
      )}
      {healthy === false && (
        <small style={{ color: "red", marginLeft: 6 }}>unhealthy</small>
      )}
    </span>
  );
}
