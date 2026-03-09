import { useAuth } from "./hooks/use-auth.ts";
import { BenchList } from "./components/bench-list.tsx";
import { Header } from "./components/header.tsx";
import { Login } from "./components/login.tsx";

export function App() {
  const { session, loading, signOut } = useAuth();

  if (loading) {
    return (
      <main className="container">
        <p aria-busy="true">Loading...</p>
      </main>
    );
  }

  if (!session) {
    return <Login />;
  }

  return (
    <>
      <Header email={session.user.email ?? ""} onSignOut={signOut} />
      <main className="container">
        <BenchList />
      </main>
    </>
  );
}
