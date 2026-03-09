#!/usr/bin/env bash
# Generate /etc/hil-bench/config.yaml from template.
set -euo pipefail

BENCH_NAME="${1:?Usage: $0 <bench-name> <repo-dir>}"
REPO_DIR="${2:?Usage: $0 <bench-name> <repo-dir>}"

CONFIG_DIR="/etc/hil-bench"
CONFIG_FILE="${CONFIG_DIR}/config.yaml"
TEMPLATE="${REPO_DIR}/configs/config.template.yaml"

echo "--- Generating local config ---"

mkdir -p "$CONFIG_DIR"

if [[ -f "$CONFIG_FILE" ]]; then
    echo "Config already exists: $CONFIG_FILE (not overwriting)"
    echo "To regenerate, delete it first: rm $CONFIG_FILE"
else
    sed \
        -e "s/my-bench-01/${BENCH_NAME}/g" \
        "$TEMPLATE" > "$CONFIG_FILE"
    echo "Generated: $CONFIG_FILE"
    echo "Edit to match your hardware, then validate:"
    echo "  benchctl config validate --config $CONFIG_FILE"
fi

echo "--- Config generation done ---"
