#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║        Proxseer Installer            ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Check macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "⚠  Proxseer is designed for macOS. Continuing anyway..."
fi

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "✗ Python 3 not found."
    echo "  Install via: brew install python3"
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PY_VERSION found"

# Create virtual environment
if [[ ! -d "$VENV_DIR" ]]; then
    echo "→ Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# Install dependencies
echo "→ Installing dependencies..."
"$VENV_DIR/bin/pip" install -q --upgrade pip
"$VENV_DIR/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
echo "✓ Dependencies installed"

# Detect local IP
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "127.0.0.1")

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║            Ready to Launch!              ║"
echo "╠══════════════════════════════════════════╣"
echo "║                                          ║"
echo "║  Web UI:  http://$LOCAL_IP:9000          "
echo "║  Proxy:   $LOCAL_IP:8080                 "
echo "║  Setup:   http://$LOCAL_IP:9000/setup    "
echo "║                                          ║"
echo "║  iPhone WiFi Proxy Settings:             ║"
echo "║    Server: $LOCAL_IP                     "
echo "║    Port:   8080                          ║"
echo "║                                          ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Starting Proxseer..."
echo "(Press Ctrl+C to stop)"
echo ""

exec "$VENV_DIR/bin/python" -m proxseer
