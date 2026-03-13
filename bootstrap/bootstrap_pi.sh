#!/usr/bin/env bash
# Master bootstrap script for HIL bench Raspberry Pi 5.
# Idempotent — safe to re-run.
#
# Usage: sudo ./bootstrap_pi.sh <bench-name> [github-org-token]
# Example: sudo ./bootstrap_pi.sh aharoni-samd51-bench-01 ghp_xxxx

set -euo pipefail

BENCH_NAME="${1:?Usage: $0 <bench-name> [github-org-token] [supabase-url] [supabase-key]}"
GITHUB_TOKEN="${2:-}"
SUPABASE_URL="${3:-}"
SUPABASE_KEY="${4:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== HIL Bench Bootstrap: ${BENCH_NAME} ==="
echo "Repo: ${REPO_DIR}"
echo ""

# Run each subscript in order
"${SCRIPT_DIR}/configure_hostname.sh" "$BENCH_NAME"
"${SCRIPT_DIR}/install_system_packages.sh"
"${SCRIPT_DIR}/install_udev_rules.sh" "$REPO_DIR"
"${SCRIPT_DIR}/install_python_env.sh" "$REPO_DIR"
"${SCRIPT_DIR}/generate_local_config.sh" "$BENCH_NAME" "$REPO_DIR"
"${SCRIPT_DIR}/install_health_timer.sh" "$REPO_DIR"

if [[ -n "$GITHUB_TOKEN" ]]; then
    "${SCRIPT_DIR}/install_runner.sh" "$BENCH_NAME" "$GITHUB_TOKEN" /etc/hil-bench/config.yaml
else
    echo "--- Skipping runner install (no token provided) ---"
    echo "Run manually: sudo ${SCRIPT_DIR}/install_runner.sh $BENCH_NAME <token>"
fi

if [[ -n "$SUPABASE_URL" ]] && [[ -n "$SUPABASE_KEY" ]]; then
    "${SCRIPT_DIR}/install_publisher.sh" "$REPO_DIR" "$SUPABASE_URL" "$SUPABASE_KEY"
else
    echo "--- Skipping publisher install (no Supabase URL/key provided) ---"
    echo "Run manually: sudo ${SCRIPT_DIR}/install_publisher.sh $REPO_DIR <url> <key>"
fi

echo ""
echo "=== Bootstrap complete for ${BENCH_NAME} ==="
echo "Config: /etc/hil-bench/config.yaml"
echo "Venv:   /opt/hil-bench/venv"
echo "Test:   /opt/hil-bench/venv/bin/benchctl --help"
