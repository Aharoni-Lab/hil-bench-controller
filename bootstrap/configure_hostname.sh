#!/usr/bin/env bash
# Set the Pi hostname to match the bench name.
set -euo pipefail

BENCH_NAME="${1:?Usage: $0 <bench-name>}"

echo "--- Configuring hostname ---"

CURRENT=$(hostname)
if [[ "$CURRENT" == "$BENCH_NAME" ]]; then
    echo "Hostname already set to $BENCH_NAME"
else
    hostnamectl set-hostname "$BENCH_NAME"
    echo "Hostname: $CURRENT → $BENCH_NAME"
fi

echo "--- Hostname done ---"
