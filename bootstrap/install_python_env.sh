#!/usr/bin/env bash
# Create Python venv and install hil-bench-controller.
set -euo pipefail

REPO_DIR="${1:?Usage: $0 <repo-dir>}"
VENV_DIR="/opt/hil-bench/venv"

echo "--- Setting up Python environment ---"

mkdir -p /opt/hil-bench

if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
    echo "Created venv at $VENV_DIR"
else
    echo "Venv already exists at $VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel -q
"$VENV_DIR/bin/pip" install -e "$REPO_DIR" -q

echo "benchctl installed: $($VENV_DIR/bin/benchctl --version)"
echo "--- Python environment done ---"
