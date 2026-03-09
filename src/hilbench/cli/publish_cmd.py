"""Supabase publisher CLI subcommands."""

from __future__ import annotations

import click
from rich.console import Console


@click.group()
def publish() -> None:
    """Publish bench status to Supabase."""


@publish.command()
@click.pass_obj
def status(ctx: object) -> None:
    """One-shot health check and publish to Supabase."""
    from hilbench.cli.main import Context
    from hilbench.health import results_to_dicts, run_all_checks
    from hilbench.publisher._client import SupabasePublisher
    from hilbench.publisher._config import load_publisher_config

    assert isinstance(ctx, Context)
    console = Console()
    cfg = ctx.config

    pub_config = load_publisher_config()
    if pub_config is None:
        console.print("[red]Publisher not configured.[/red] Set SUPABASE_URL/KEY env vars.")
        raise SystemExit(1)

    results = run_all_checks(cfg)
    all_passed = all(r.passed for r in results)
    checks = results_to_dicts(results)
    state = "idle" if all_passed else "error"

    publisher = SupabasePublisher(pub_config, cfg)
    publisher.publish_status(state=state, healthy=all_passed, checks=checks)
    publisher.publish_event("health_check", {"healthy": all_passed, "checks": checks})
    publisher.close()

    console.print(f"[green]Published:[/green] state={state} healthy={all_passed}")


@publish.command()
@click.pass_obj
def heartbeat(ctx: object) -> None:
    """Run continuous heartbeat loop (for systemd)."""
    from hilbench.cli.main import Context
    from hilbench.publisher._client import SupabasePublisher
    from hilbench.publisher._config import load_publisher_config
    from hilbench.publisher._heartbeat import run_heartbeat_loop

    assert isinstance(ctx, Context)
    console = Console()
    cfg = ctx.config

    pub_config = load_publisher_config()
    if pub_config is None:
        console.print("[red]Publisher not configured.[/red] Set SUPABASE_URL/KEY env vars.")
        raise SystemExit(1)

    publisher = SupabasePublisher(pub_config, cfg)
    run_heartbeat_loop(publisher, cfg, interval_s=pub_config.heartbeat_interval_s)


@publish.command("config")
def show_config() -> None:
    """Show publisher configuration (password redacted)."""
    from hilbench.publisher._config import load_publisher_config

    console = Console()
    pub_config = load_publisher_config()
    if pub_config is None:
        console.print("Publisher not configured. Required env vars:")
        console.print("  SUPABASE_URL, SUPABASE_KEY, BENCH_EMAIL, BENCH_PASSWORD")
        return

    console.print(f"  supabase_url:        {pub_config.supabase_url}")
    console.print(f"  supabase_key:        {pub_config.supabase_key[:8]}...")
    console.print(f"  bench_email:         {pub_config.bench_email}")
    console.print("  bench_password:      ********")
    console.print(f"  heartbeat_interval:  {pub_config.heartbeat_interval_s}s")
    console.print(f"  publish_events:      {pub_config.publish_events}")
    console.print(f"  enabled:             {pub_config.enabled}")
