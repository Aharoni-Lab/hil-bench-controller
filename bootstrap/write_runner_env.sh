#!/usr/bin/env bash
# Write the runner .env file so jobs see the venv on PATH.
# Usage: write_runner_env.sh <runner-dir> <venv> <config-path>
set -euo pipefail

RUNNER_DIR="${1:?Usage: $0 <runner-dir> <venv> <config-path>}"
VENV="${2:?Usage: $0 <runner-dir> <venv> <config-path>}"
CONFIG_PATH="${3:?Usage: $0 <runner-dir> <venv> <config-path>}"

cat > "$RUNNER_DIR/.env" <<ENVEOF
PATH=${VENV}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
VIRTUAL_ENV=${VENV}
HIL_BENCH_CONFIG=${CONFIG_PATH}
ENVEOF
echo "Wrote ${RUNNER_DIR}/.env"
