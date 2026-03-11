#!/usr/bin/env bash
# Install system-level dependencies for HIL bench.
set -euo pipefail

echo "--- Installing system packages ---"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    gpiod \
    libgpiod-dev \
    python3-venv \
    python3-dev \
    openocd \
    git \
    build-essential \
    usbutils

# Build edbg from source if not already installed
if ! command -v edbg &>/dev/null; then
    echo "Building edbg from source..."
    EDBG_DIR=$(mktemp -d)
    git clone --depth 1 https://github.com/ataradov/edbg.git "$EDBG_DIR"
    make -C "$EDBG_DIR" all
    install -m 755 "$EDBG_DIR/edbg" /usr/local/bin/edbg
    rm -rf "$EDBG_DIR"
    echo "edbg installed: $(edbg --version 2>&1 || true)"
else
    echo "edbg already installed: $(edbg --version 2>&1 || true)"
fi

echo "--- System packages done ---"
