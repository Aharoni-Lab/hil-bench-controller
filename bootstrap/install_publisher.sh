#!/usr/bin/env bash
# Install the Supabase publisher and heartbeat service.
# Idempotent — safe to re-run.
#
# Usage: sudo ./install_publisher.sh <repo-dir> [supabase-url] [supabase-key]
set -euo pipefail

REPO_DIR="${1:?Usage: $0 <repo-dir> [supabase-url] [supabase-key]}"
SUPABASE_URL="${2:-}"
SUPABASE_KEY="${3:-}"
VENV="/opt/hil-bench/venv"
ENV_FILE="/etc/hil-bench/supabase.env"
CONFIG_FILE="/etc/hil-bench/config.yaml"
SYSTEMD_DST="/etc/systemd/system"

echo "--- Installing Supabase publisher ---"

# Install supabase package into venv
if [[ -d "$VENV" ]]; then
    echo "Installing supabase package..."
    "${VENV}/bin/pip" install --quiet "supabase>=2.11"
else
    echo "WARNING: venv not found at $VENV — run install_python_env.sh first"
fi

# Generate credentials file if URL/key provided and file doesn't exist
if [[ -n "$SUPABASE_URL" ]] && [[ -n "$SUPABASE_KEY" ]] && [[ ! -f "$ENV_FILE" ]]; then
    # Read bench_name from existing config
    BENCH_NAME=""
    if [[ -f "$CONFIG_FILE" ]]; then
        BENCH_NAME=$(grep -m1 'bench_name:' "$CONFIG_FILE" | awk '{print $2}' || true)
    fi

    echo "Generating ${ENV_FILE}..."
    mkdir -p "$(dirname "$ENV_FILE")"
    cat > "$ENV_FILE" <<ENVEOF
# Supabase credentials for HIL bench publisher
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_KEY=${SUPABASE_KEY}
BENCH_EMAIL=${BENCH_NAME}@hil-bench.local
BENCH_PASSWORD=CHANGE_ME
ENVEOF
    chmod 600 "$ENV_FILE"
    echo "Created ${ENV_FILE} — edit BENCH_EMAIL and BENCH_PASSWORD"
elif [[ -f "$ENV_FILE" ]]; then
    echo "Credentials file exists: ${ENV_FILE} (skipping)"
fi

# Install systemd unit
UNIT_SRC="${REPO_DIR}/systemd/hil-bench-publisher.service"
if [[ -f "$UNIT_SRC" ]]; then
    cp "$UNIT_SRC" "${SYSTEMD_DST}/hil-bench-publisher.service"
    systemctl daemon-reload
    echo "Installed: ${SYSTEMD_DST}/hil-bench-publisher.service"

    if [[ -f "$ENV_FILE" ]]; then
        systemctl enable hil-bench-publisher.service
        echo "Publisher service enabled (start with: systemctl start hil-bench-publisher)"
    else
        echo "Publisher service installed but NOT enabled (no credentials file)"
    fi
else
    echo "WARNING: Service file not found: $UNIT_SRC"
fi

echo ""
echo "Next steps:"
echo "  1. Create a bench user in Supabase Auth dashboard"
echo "     - Set email/password matching ${ENV_FILE}"
echo "     - Add user_metadata: {\"bench_name\": \"<your-bench-name>\"}"
echo "  2. Edit ${ENV_FILE} with correct credentials"
echo "  3. Start the service: sudo systemctl start hil-bench-publisher"
echo "--- Publisher install done ---"
