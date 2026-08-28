#!/bin/sh
set -eu

MARKER="node_modules/.deps-fingerprint"
CURRENT="$(cksum package-lock.json | awk '{print $1"-"$2}')"

if [ ! -d node_modules ] || [ ! -f "$MARKER" ] || [ "$(cat "$MARKER")" != "$CURRENT" ]; then
  echo "Installing frontend dependencies..."
  npm ci --no-audit --no-fund
  mkdir -p node_modules
  echo "$CURRENT" > "$MARKER"
fi

exec "$@"
