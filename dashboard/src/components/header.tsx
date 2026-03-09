interface HeaderProps {
  email: string;
  onSignOut: () => void;
}

export function Header({ email, onSignOut }: HeaderProps) {
  return (
    <header className="container">
      <nav>
        <ul>
          <li>
            <strong>HIL Bench Dashboard</strong>
          </li>
        </ul>
        <ul>
          <li>
            <small>{email}</small>
          </li>
          <li>
            <button className="outline secondary" onClick={onSignOut}>
              Sign Out
            </button>
          </li>
        </ul>
      </nav>
    </header>
  );
}
