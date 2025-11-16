#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for /dev/cu.usbmodem* or /dev/tty.usbmodem* ..." >&2
PORT=""
while [[ -z "${PORT}" ]]; do
  PORT=$(ls /dev/cu.usbmodem* 2>/dev/null | head -n1 || ls /dev/tty.usbmodem* 2>/dev/null | head -n1 || true)
  sleep 0.05
done
echo "Found ${PORT}, arming DISABLE..." >&2
sleep 0.1

# Keep the port open and blast DISABLE for ~0.6s to hit early window
exec 3>"$PORT" || true
for i in {1..60}; do
  printf 'DISABLE\n' >&3 || true
  sleep 0.01
done
exec 3>&-

echo "Sent DISABLE to $PORT"
