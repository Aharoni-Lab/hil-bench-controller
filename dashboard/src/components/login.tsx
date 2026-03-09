import { type FormEvent, useState } from "react";
import { supabase } from "../supabase.ts";

export function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const { error: err } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  return (
    <main className="container">
      <article style={{ maxWidth: 400, margin: "4rem auto" }}>
        <header>
          <h2>HIL Bench Dashboard</h2>
        </header>
        <form onSubmit={(e) => void handleSubmit(e)}>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          {error && <p style={{ color: "var(--pico-color-red-500)" }}>{error}</p>}
          <button type="submit" aria-busy={loading} disabled={loading}>
            Sign In
          </button>
        </form>
      </article>
    </main>
  );
}
