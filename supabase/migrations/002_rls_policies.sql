-- Row Level Security policies for HIL bench tables.
-- Viewers: any authenticated user can SELECT.
-- Bench writers: matched via auth.jwt()->'user_metadata'->>'bench_name'.

-- ── Enable RLS ──────────────────────────────────────────────────────────────

alter table benches enable row level security;
alter table bench_status_current enable row level security;
alter table bench_events enable row level security;

-- ── Viewer policies (SELECT for any authenticated user) ─────────────────────

create policy "Authenticated users can view benches"
    on benches for select
    to authenticated
    using (true);

create policy "Authenticated users can view bench status"
    on bench_status_current for select
    to authenticated
    using (true);

create policy "Authenticated users can view bench events"
    on bench_events for select
    to authenticated
    using (true);

-- ── Bench writer policies ───────────────────────────────────────────────────

-- benches: INSERT own row
create policy "Bench can insert own registration"
    on benches for insert
    to authenticated
    with check (bench_name = auth.jwt()->'user_metadata'->>'bench_name');

-- benches: UPDATE own row
create policy "Bench can update own registration"
    on benches for update
    to authenticated
    using (bench_name = auth.jwt()->'user_metadata'->>'bench_name')
    with check (bench_name = auth.jwt()->'user_metadata'->>'bench_name');

-- bench_status_current: INSERT own row (via bench_id lookup)
create policy "Bench can insert own status"
    on bench_status_current for insert
    to authenticated
    with check (
        bench_id in (
            select id from benches
            where bench_name = auth.jwt()->'user_metadata'->>'bench_name'
        )
    );

-- bench_status_current: UPDATE own row
create policy "Bench can update own status"
    on bench_status_current for update
    to authenticated
    using (
        bench_id in (
            select id from benches
            where bench_name = auth.jwt()->'user_metadata'->>'bench_name'
        )
    )
    with check (
        bench_id in (
            select id from benches
            where bench_name = auth.jwt()->'user_metadata'->>'bench_name'
        )
    );

-- bench_events: INSERT own rows
create policy "Bench can insert own events"
    on bench_events for insert
    to authenticated
    with check (
        bench_id in (
            select id from benches
            where bench_name = auth.jwt()->'user_metadata'->>'bench_name'
        )
    );
