# Publisher Architecture

## Design Principles

1. **Non-disruptive**: All publisher operations swallow exceptions. A bench must continue operating even if Supabase is unreachable.
2. **Opt-in**: Publisher is only active when credentials are configured. No behavior change for benches without Supabase.
3. **Portable**: Any group can clone the repo, create their own Supabase project, run the migrations, and have a working dashboard.

## Module Structure

```
src/hilbench/publisher/
  __init__.py          Public API: on_flash_start, on_flash_end, on_health_complete
  _config.py           PublisherConfig model, env file loader
  _models.py           Pydantic models for Supabase table payloads
  _client.py           SupabasePublisher class (lazy init, exception-safe)
  _hooks.py            Hook functions with module-level singleton
  _heartbeat.py        Continuous heartbeat loop for systemd
```

## Auth Flow

1. Each bench has a dedicated Supabase Auth user with `bench_name` in `user_metadata`.
2. The publisher signs in with email/password on first use (lazy).
3. RLS policies match the JWT's `user_metadata.bench_name` to restrict writes to own rows.
4. Dashboard users are separate Auth users — any authenticated user can view all benches.

## Hook Integration

CLI commands call publisher hooks wrapped in `try/except ImportError`:

- **flash_cmd.py**: `on_flash_start` before flash, `on_flash_end` after (success or failure)
- **health_cmd.py**: `on_health_complete` after health checks
- **publish_cmd.py**: Direct `publish status` and `publish heartbeat` subcommands

The `ImportError` catch ensures the CLI works even without the `supabase` package installed.

## Event Gating

Event publishing (`bench_events` table) is controlled by the `PUBLISH_EVENTS` env var (default: false). Status publishing (`bench_status_current`) is always active when the publisher is configured.

## Heartbeat

The `hil-bench-publisher.service` runs `benchctl publish heartbeat`, which:

1. Runs `run_all_checks()` from `hilbench.health`
2. Publishes status to `bench_status_current`
3. Optionally publishes a `heartbeat` event
4. Sleeps for `HEARTBEAT_INTERVAL_S` (default 60s)
5. Repeats until SIGTERM/SIGINT

The dashboard considers a heartbeat stale if older than 3 minutes.
