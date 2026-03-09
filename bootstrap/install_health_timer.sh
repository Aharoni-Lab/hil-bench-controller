#!/usr/bin/env bash
# Install and enable the HIL bench health check systemd timer.
set -euo pipefail

REPO_DIR="${1:?Usage: $0 <repo-dir>}"
SYSTEMD_SRC="${REPO_DIR}/systemd"
SYSTEMD_DST="/etc/systemd/system"

echo "--- Installing health check timer ---"

for unit in hil-bench-health.service hil-bench-health.timer; do
    src="${SYSTEMD_SRC}/${unit}"
    if [[ ! -f "$src" ]]; then
        echo "ERROR: Unit file not found: $src"
        exit 1
    fi
    cp "$src" "${SYSTEMD_DST}/${unit}"
    echo "Installed: ${SYSTEMD_DST}/${unit}"
done

systemctl daemon-reload
systemctl enable --now hil-bench-health.timer

echo "Health timer enabled (runs 1 min after boot, then every 5 min)"
echo "--- Health timer install done ---"
