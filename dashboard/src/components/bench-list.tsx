import { useBenches } from "../hooks/use-benches.ts";
import { BenchCard } from "./bench-card.tsx";

export function BenchList() {
  const { benches, loading, error } = useBenches();

  if (loading) {
    return <p aria-busy="true">Loading benches...</p>;
  }

  if (error) {
    return <p style={{ color: "var(--pico-color-red-500)" }}>Error: {error}</p>;
  }

  if (benches.length === 0) {
    return <p>No benches registered yet.</p>;
  }

  return (
    <figure>
      <table role="grid">
        <thead>
          <tr>
            <th>Bench</th>
            <th>Status</th>
            <th>Last Heartbeat</th>
            <th>Detail</th>
            <th>Labels</th>
            <th>Links</th>
          </tr>
        </thead>
        <tbody>
          {benches.map((bench) => (
            <BenchCard key={bench.id} bench={bench} />
          ))}
        </tbody>
      </table>
    </figure>
  );
}
