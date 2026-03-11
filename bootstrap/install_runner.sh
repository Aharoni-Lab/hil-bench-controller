#!/usr/bin/env bash
# Download and configure GitHub Actions runner at org scope.
# Must be run as root (for service install), but drops to SUDO_USER for config.
set -euo pipefail

BENCH_NAME="${1:?Usage: $0 <bench-name> <github-token> <github-org>}"
GITHUB_TOKEN="${2:?Usage: $0 <bench-name> <github-token> <github-org>}"
ORG="${3:?Usage: $0 <bench-name> <github-token> <github-org>}"

RUNNER_DIR="/opt/hil-bench/actions-runner"
RUNNER_VERSION="2.321.0"
RUNNER_USER="${SUDO_USER:-$(whoami)}"

echo "--- Installing GitHub Actions runner (org: ${ORG}, user: ${RUNNER_USER}) ---"

mkdir -p "$RUNNER_DIR"
chown -R "$RUNNER_USER" "$RUNNER_DIR"

# Download runner if not present
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
    sudo -u "$RUNNER_USER" bash -c "curl -sL '$URL' | tar xz -C '$RUNNER_DIR'"
fi

# Configure runner at org level (idempotent — skips if .runner exists)
# Must run as non-root — the runner refuses to configure as root.
if [[ ! -f "$RUNNER_DIR/.runner" ]]; then
    echo "Configuring runner for org ${ORG}..."
    sudo -u "$RUNNER_USER" "$RUNNER_DIR/config.sh" \
        --url "https://github.com/${ORG}" \
        --token "$GITHUB_TOKEN" \
        --name "$BENCH_NAME" \
        --labels "self-hosted,linux,ARM64,hil,$(echo "$BENCH_NAME" | tr '-' ',')" \
        --work /opt/hil-bench/_work \
        --unattended \
        --replace
else
    echo "Runner already configured"
fi

# Install and start systemd service (requires root)
if ! systemctl is-enabled "actions.runner.${ORG}.${BENCH_NAME}.service" &>/dev/null; then
    cd "$RUNNER_DIR"
    ./svc.sh install "$RUNNER_USER"
    ./svc.sh start
    echo "Runner service installed and started"
else
    echo "Runner service already running"
fi

echo "--- Runner install done ---"
