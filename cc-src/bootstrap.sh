#!/bin/bash
set -euo pipefail

LISTENER_URL="https://raw.githubusercontent.com/JBlitzar/picoducky/refs/heads/main/cc-src/listener.py"

if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "bruh no python" >&2
    exit 1
fi

curl -sSL "$LISTENER_URL" | "$PYTHON" -