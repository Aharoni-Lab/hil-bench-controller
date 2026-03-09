import type { BenchDashboardRow } from "../types.ts";
import { StatusBadge } from "./status-badge.tsx";

function formatAge(isoDate: string | null): string {
  if (!isoDate) return "never";
  const diff = Date.now() - new Date(isoDate).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

interface BenchCardProps {
  bench: BenchDashboardRow;
}

export function BenchCard({ bench }: BenchCardProps) {
  return (
    <tr>
      <td>
        <strong>{bench.bench_name}</strong>
        {bench.hostname && bench.hostname !== bench.bench_name && (
          <br />
        )}
        {bench.hostname && bench.hostname !== bench.bench_name && (
          <small>{bench.hostname}</small>
        )}
      </td>
      <td>
        <StatusBadge
          state={bench.state}
          healthy={bench.healthy}
          stale={bench.stale}
        />
      </td>
      <td>{formatAge(bench.last_heartbeat)}</td>
      <td>{bench.detail ?? ""}</td>
      <td>
        {bench.labels.length > 0 && (
          <small>{bench.labels.join(", ")}</small>
        )}
      </td>
      <td>
        {bench.wiki_url && (
          <a href={bench.wiki_url} target="_blank" rel="noopener noreferrer">
            Wiki
          </a>
        )}
      </td>
    </tr>
  );
}
