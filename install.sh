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

# Find Python >= 3.10 (required by mitmproxy >= 10.0)
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" &>/dev/null; then
        minor=$("$candidate" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null) || continue
        if [[ "$minor" -ge 10 ]]; then
            PYTHON="$(command -v "$candidate")"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    echo "✗ Python 3.10+ not found (required by mitmproxy >= 10.0)."
    echo "  Install via: brew install python@3.12"
    exit 1
fi

PY_VERSION=$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PY_VERSION found ($PYTHON)"

# Create virtual environment
if [[ ! -d "$VENV_DIR" ]]; then
    echo "→ Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# Install dependencies
echo "→ Installing dependencies..."
"$VENV_DIR/bin/pip" install -q --upgrade pip
"$VENV_DIR/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
echo "✓ Dependencies installed"

# Verify mitmproxy installation
if "$VENV_DIR/bin/python" -c "import mitmproxy" &>/dev/null; then
    MITM_VERSION=$("$VENV_DIR/bin/python" -c "from mitmproxy.version import VERSION; print(VERSION)")
    echo "✓ mitmproxy $MITM_VERSION installed"
else
    echo "✗ mitmproxy failed to install."
    echo "  Try: $VENV_DIR/bin/pip install mitmproxy>=10.0"
    exit 1
fi

if [[ ! -x "$VENV_DIR/bin/mitmdump" ]]; then
    echo "⚠  mitmdump binary not found in venv. mitmproxy may not work correctly."
fi

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
