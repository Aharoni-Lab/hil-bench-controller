-- HIL Bench Controller — Supabase Schema
-- Run via Supabase SQL editor or supabase db push.

-- ── Tables ──────────────────────────────────────────────────────────────────

create table if not exists benches (
    id          uuid primary key default gen_random_uuid(),
    bench_name  text unique not null,
    hostname    text,
    labels      text[] default '{}',
    targets     jsonb default '{}',
    wiki_url    text,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create table if not exists bench_status_current (
    bench_id        uuid primary key references benches(id) on delete cascade,
    state           text not null default 'unknown'
                    check (state in ('idle', 'flashing', 'testing', 'error', 'offline', 'unknown')),
    healthy         boolean not null default false,
    checks          jsonb default '[]',
    last_heartbeat  timestamptz not null default now(),
    detail          text,
    updated_at      timestamptz not null default now()
);

create table if not exists bench_events (
    id          bigint generated always as identity primary key,
    bench_id    uuid not null references benches(id) on delete cascade,
    event_type  text not null,
    payload     jsonb default '{}',
    created_at  timestamptz not null default now()
);

-- ── Indexes ─────────────────────────────────────────────────────────────────

create index if not exists idx_bench_status_heartbeat
    on bench_status_current (last_heartbeat desc);

create index if not exists idx_bench_events_bench_created
    on bench_events (bench_id, created_at desc);

-- ── updated_at trigger ──────────────────────────────────────────────────────

create or replace function set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create or replace trigger trg_benches_updated_at
    before update on benches
    for each row execute function set_updated_at();

create or replace trigger trg_bench_status_updated_at
    before update on bench_status_current
    for each row execute function set_updated_at();
