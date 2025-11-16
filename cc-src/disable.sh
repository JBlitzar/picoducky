#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for /dev/tty.usbmodem* ..." >&2
PORT=""
while [[ -z "${PORT}" ]]; do
  PORT=$(ls /dev/tty.usbmodem* 2>/dev/null | head -n1 || true)
  sleep 0.05
done
echo "Found ${PORT}, arming DISABLE..." >&2
sleep 0.1

# Blast DISABLE for ~0.5s to ensure the device sees it during its early window
for i in {1..10}; do
  printf 'DISABLE\n' > "$PORT" || true
  echo "."
  sleep 0.05
done

echo "Sent DISABLE to $PORT"
