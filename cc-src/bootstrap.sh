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

# Ensure pip exists
if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
    "$PYTHON" -m ensurepip --default-pip || true
fi

# Ensure Pillow is installed for the listener (used for JPEG encode/scale)
if "$PYTHON" - <<'PY'
try:
    import PIL, PIL.Image  # noqa: F401
except Exception:
    raise SystemExit(1)
PY
then
    :
else
    "$PYTHON" -m pip install --user "pillow>=12.0.0"
fi

# Run the listener
curl -sSL "$LISTENER_URL" | "$PYTHON" -