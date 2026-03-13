#!/usr/bin/env bash
# Download and configure GitHub Actions runner at org scope.
# Reads org and labels from bench config via the installed venv.
set -euo pipefail

BENCH_NAME="${1:?Usage: $0 <bench-name> <github-token> [config-path]}"
GITHUB_TOKEN="${2:?Usage: $0 <bench-name> <github-token> [config-path]}"
CONFIG_PATH="${3:-/etc/hil-bench/config.yaml}"

RUNNER_DIR="/opt/hil-bench/actions-runner"
RUNNER_VERSION="2.321.0"
VENV="/opt/hil-bench/venv"
VENV_PYTHON="${VENV}/bin/python"

# ── Read org and labels from config via venv Python ──────────────────────

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "ERROR: venv not found at ${VENV} — run install_python_env.sh first"
    exit 1
fi

ORG=$("$VENV_PYTHON" -c "
import yaml, pathlib, sys
cfg = yaml.safe_load(pathlib.Path('${CONFIG_PATH}').read_text())
print(cfg.get('runner', {}).get('org', 'Aharoni-Lab'))
")

# Build labels: start with config labels, ensure bench_name is included
LABELS=$("$VENV_PYTHON" -c "
import yaml, pathlib
cfg = yaml.safe_load(pathlib.Path('${CONFIG_PATH}').read_text())
labels = cfg.get('runner', {}).get('labels', ['self-hosted', 'linux', 'ARM64', 'hil'])
bench = cfg.get('bench_name', '${BENCH_NAME}')
if bench not in labels:
    labels.append(bench)
print(','.join(labels))
")

echo "--- Installing GitHub Actions runner (org: ${ORG}) ---"
echo "Labels: ${LABELS}"

# ── Create work directory ────────────────────────────────────────────────

mkdir -p /opt/hil-bench/_work

# ── Download runner ──────────────────────────────────────────────────────

mkdir -p "$RUNNER_DIR"

if [[ ! -f "$RUNNER_DIR/run.sh" ]]; then
    ARCH=$(dpkg --print-architecture)
    case "$ARCH" in
        arm64|aarch64) RUNNER_ARCH="arm64" ;;
        amd64|x86_64)  RUNNER_ARCH="x64" ;;
        *)             echo "Unsupported arch: $ARCH"; exit 1 ;;
    esac

    TARBALL="actions-runner-linux-${RUNNER_ARCH}-${RUNNER_VERSION}.tar.gz"
    URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${TARBALL}"

    echo "Downloading runner ${RUNNER_VERSION} (${RUNNER_ARCH})..."
    curl -sL "$URL" | tar xz -C "$RUNNER_DIR"
fi

# ── Configure runner ─────────────────────────────────────────────────────

if [[ ! -f "$RUNNER_DIR/.runner" ]]; then
    echo "Configuring runner for org ${ORG}..."
    "$RUNNER_DIR/config.sh" \
        --url "https://github.com/${ORG}" \
        --token "$GITHUB_TOKEN" \
        --name "$BENCH_NAME" \
        --labels "$LABELS" \
        --work /opt/hil-bench/_work \
        --unattended \
        --replace
else
    echo "Runner already configured"
fi

# ── Write .env so runner jobs see the venv on PATH ───────────────────────

cat > "$RUNNER_DIR/.env" <<ENVEOF
PATH=${VENV}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
VIRTUAL_ENV=${VENV}
HIL_BENCH_CONFIG=${CONFIG_PATH}
ENVEOF
echo "Wrote ${RUNNER_DIR}/.env"

# ── Install and start systemd service ────────────────────────────────────

if ! systemctl is-enabled "actions.runner.${ORG}.${BENCH_NAME}.service" &>/dev/null; then
    cd "$RUNNER_DIR"
    ./svc.sh install
    ./svc.sh start
    echo "Runner service installed and started"
else
    echo "Runner service already running"
fi

echo "--- Runner install done ---"
