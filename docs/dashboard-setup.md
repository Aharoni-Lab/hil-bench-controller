# Status Dashboard Setup Guide

Set up Supabase-backed remote monitoring for your HIL benches with a GitHub Pages dashboard.

## 1. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project.
2. Note the **Project URL** and **anon public** API key from Settings → API.

## 2. Run Migrations

Open the SQL Editor in the Supabase dashboard and run each migration file in order:

1. `supabase/migrations/001_create_tables.sql` — creates `benches`, `bench_status_current`, `bench_events` tables
2. `supabase/migrations/002_rls_policies.sql` — enables row-level security
3. `supabase/migrations/003_dashboard_view.sql` — creates the `bench_dashboard` view

## 3. Create Bench Users

For each bench Pi, create a user in Supabase Auth:

1. Go to Authentication → Users → Add user
2. Set email (e.g., `bench-01@your-domain.com`) and password
3. In user metadata, add: `{"bench_name": "your-bench-name"}`

The `bench_name` in metadata must match the `bench_name` in the bench's `config.yaml`.

## 4. Configure Each Pi

On each Pi, create `/etc/hil-bench/supabase.env`:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
BENCH_EMAIL=bench-01@your-domain.com
BENCH_PASSWORD=the-password-you-set
```

Set permissions:

```bash
sudo chmod 600 /etc/hil-bench/supabase.env
```

Or use the bootstrap script:

```bash
sudo ./bootstrap/install_publisher.sh /path/to/repo https://your-project.supabase.co your-anon-key
```

## 5. Install and Start Publisher

```bash
# Install supabase package
/opt/hil-bench/venv/bin/pip install "supabase>=2.11"

# Test one-shot publish
benchctl publish status

# Enable heartbeat service
sudo systemctl enable --now hil-bench-publisher
```

## 6. Deploy Dashboard

### GitHub Pages (recommended)

1. Add repository secrets:
   - `VITE_SUPABASE_URL` — your project URL
   - `VITE_SUPABASE_ANON_KEY` — your anon key

2. Enable GitHub Pages (Settings → Pages → Source: GitHub Actions)

3. Create a release tag:
   ```bash
   git tag dashboard-v0.1.0
   git push origin dashboard-v0.1.0
   ```

### Local Development

```bash
cd dashboard
cp .env.example .env
# Edit .env with your Supabase credentials
npm install
npm run dev
```

## 7. Verify

1. Check bench registration: `benchctl publish config`
2. Run one-shot publish: `benchctl publish status`
3. Verify in Supabase: check the `bench_dashboard` view in Table Editor
4. Open the dashboard URL and sign in
5. Confirm your bench appears with current state and heartbeat
