import { useEffect, useState } from "react";
import { supabase } from "../supabase.ts";
import type { BenchDashboardRow } from "../types.ts";

const POLL_INTERVAL_MS = 15_000;

export function useBenches() {
  const [benches, setBenches] = useState<BenchDashboardRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const fetchBenches = async () => {
      const { data, error: err } = await supabase
        .from("bench_dashboard")
        .select("*")
        .order("bench_name");

      if (!active) return;

      if (err) {
        setError(err.message);
      } else {
        setBenches(data as BenchDashboardRow[]);
        setError(null);
      }
      setLoading(false);
    };

    void fetchBenches();
    const interval = setInterval(() => void fetchBenches(), POLL_INTERVAL_MS);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  return { benches, loading, error };
}
