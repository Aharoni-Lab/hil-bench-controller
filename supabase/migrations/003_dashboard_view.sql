-- Dashboard view joining benches + status with stale heartbeat detection.

create or replace view bench_dashboard as
select
    b.id,
    b.bench_name,
    b.hostname,
    b.labels,
    b.targets,
    b.wiki_url,
    s.state,
    s.healthy,
    s.checks,
    s.last_heartbeat,
    s.detail,
    -- Heartbeat older than 3 minutes is considered stale
    coalesce(s.last_heartbeat < now() - interval '3 minutes', true) as stale,
    b.updated_at
from benches b
left join bench_status_current s on s.bench_id = b.id;
