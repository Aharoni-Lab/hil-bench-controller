#!/usr/bin/env bash
# Install the LED daemon service.
# Idempotent — safe to re-run.
#
# Usage: sudo ./install_led_service.sh <repo-dir>
set -euo pipefail

REPO_DIR="${1:?Usage: $0 <repo-dir>}"
VENV="/opt/hil-bench/venv"
SYSTEMD_DST="/etc/systemd/system"

echo "--- Installing LED service ---"

# Install rpi_ws281x into venv
if [[ -d "$VENV" ]]; then
    echo "Installing rpi_ws281x package..."
    "${VENV}/bin/pip" install --quiet "rpi_ws281x>=5.0"
else
    echo "WARNING: venv not found at $VENV — run install_python_env.sh first"
fi

# Install systemd unit
UNIT_SRC="${REPO_DIR}/systemd/hil-bench-led.service"
if [[ -f "$UNIT_SRC" ]]; then
    cp "$UNIT_SRC" "${SYSTEMD_DST}/hil-bench-led.service"
    systemctl daemon-reload
    systemctl enable hil-bench-led.service
    echo "Installed and enabled: ${SYSTEMD_DST}/hil-bench-led.service"
else
    echo "WARNING: Service file not found: $UNIT_SRC"
fi

echo "--- LED service install done ---"
echo "Start with: sudo systemctl start hil-bench-led"
