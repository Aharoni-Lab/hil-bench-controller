#!/usr/bin/env bash
# Install udev rules for HIL bench hardware.
set -euo pipefail

REPO_DIR="${1:?Usage: $0 <repo-dir>}"
RULES_SRC="${REPO_DIR}/udev/99-hil-bench.rules"
RULES_DST="/etc/udev/rules.d/99-hil-bench.rules"

echo "--- Installing udev rules ---"

if [[ ! -f "$RULES_SRC" ]]; then
    echo "ERROR: Rules file not found: $RULES_SRC"
    exit 1
fi

cp "$RULES_SRC" "$RULES_DST"
udevadm control --reload-rules
udevadm trigger

echo "Installed: $RULES_DST"
echo "--- udev rules done ---"
