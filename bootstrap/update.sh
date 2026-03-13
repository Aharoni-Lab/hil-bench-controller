#!/usr/bin/env bash
# Lightweight idempotent update script.
# Run after `git pull` to apply code + config changes without re-registering
# the runner or touching /etc/hil-bench/config.yaml.
#
# Usage: sudo ./bootstrap/update.sh [config-path]
set -euo pipefail

CONFIG_PATH="${1:-/etc/hil-bench/config.yaml}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
VENV="/opt/hil-bench/venv"
RUNNER_DIR="/opt/hil-bench/actions-runner"

echo "=== HIL Bench Update ==="
echo "Repo: ${REPO_DIR}"
echo "Config: ${CONFIG_PATH}"
echo ""

# ── 1. Reinstall benchctl into venv ──────────────────────────────────────

if [[ -d "$VENV" ]]; then
    echo "--- Updating benchctl in venv ---"
    "${VENV}/bin/pip" install --quiet -e "$REPO_DIR"
    echo "benchctl updated"
else
    echo "WARNING: venv not found at ${VENV} — run install_python_env.sh first"
fi

# ── 2. Ensure work directory exists ──────────────────────────────────────

mkdir -p /opt/hil-bench/_work
echo "Work directory: /opt/hil-bench/_work"

# ── 3. Refresh runner .env (if runner is installed) ──────────────────────

if [[ -d "$RUNNER_DIR" ]]; then
    echo "--- Refreshing runner .env ---"
    "${SCRIPT_DIR}/write_runner_env.sh" "$RUNNER_DIR" "$VENV" "$CONFIG_PATH"
else
    echo "Runner not installed — skipping .env"
fi

# ── 4. Refresh systemd health timer ─────────────────────────────────────

echo "--- Refreshing health timer ---"
"${SCRIPT_DIR}/install_health_timer.sh" "$REPO_DIR"

# ── 5. Refresh udev rules ─────────────────────────────────────────────

echo "--- Refreshing udev rules ---"
"${SCRIPT_DIR}/install_udev_rules.sh" "$REPO_DIR"

# ── 6. Refresh LED service ───────────────────────────────────────────

LED_UNIT_SRC="${REPO_DIR}/systemd/hil-bench-led.service"
if [[ -f "$LED_UNIT_SRC" ]]; then
    echo "--- Refreshing LED service ---"
    cp "$LED_UNIT_SRC" /etc/systemd/system/hil-bench-led.service
    systemctl daemon-reload
    echo "LED service unit refreshed"
fi

# ── 7. Done ──────────────────────────────────────────────────────────────

echo ""
echo "=== Update complete ==="
if [[ -d "$RUNNER_DIR" ]]; then
    echo "REMINDER: Restart the runner service to pick up changes:"
    echo "  sudo systemctl restart actions.runner.*.service"
fi
