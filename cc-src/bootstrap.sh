#!/bin/bash

LISTENER_URL = "https://raw.githubusercontent.com/jblitzar/picoducky/main/cc-src/listener.py"

if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "Error: Neither python nor python3 found in PATH" >&2
    exit 1
fi

curl -sSL $LISTENER_URL | $PYTHON -