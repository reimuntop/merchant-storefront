#!/usr/bin/env bash
# stop-local.sh - hentikan backend dan Vite yang dijalankan run-local.sh.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
FRONT="$ROOT/frontend"

for pidfile in "$ROOT/backend.pid" "$FRONT/_meta/preview.pid" "$FRONT/_meta/dev.pid"; do
  [ -f "$pidfile" ] || continue
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.5
    done
    kill -9 "$pid" 2>/dev/null || true
    printf '[+] stopped pid %s (%s)\n' "$pid" "$pidfile"
  fi
  rm -f "$pidfile"
done

# Vite preview/dev adalah child dari npm; bersihkan sisa proses pada port lokal.
for port in 8000 4173 5173; do
  pids="$(ss -ltnp 2>/dev/null | awk -v p=":$port" '$4 ~ p {print $0}' | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)"
  for pid in $pids; do
    kill "$pid" 2>/dev/null || true
    printf '[+] stopped listener pid %s on :%s\n' "$pid" "$port"
  done
done

printf '[=] selesai\n'
