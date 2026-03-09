export interface CheckResult {
  name: string;
  passed: boolean;
  detail: string;
}

export interface BenchDashboardRow {
  id: string;
  bench_name: string;
  hostname: string | null;
  labels: string[];
  targets: Record<string, unknown>;
  wiki_url: string | null;
  state: string | null;
  healthy: boolean | null;
  checks: CheckResult[];
  last_heartbeat: string | null;
  detail: string | null;
  stale: boolean;
  updated_at: string;
}

export type BenchState =
  | "idle"
  | "flashing"
  | "testing"
  | "error"
  | "offline"
  | "unknown";
