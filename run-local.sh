#!/usr/bin/env bash
# run-local.sh - jalankan backend :8000 + Vite preview :4173.
# Gunakan --dev untuk Vite dev server :5173.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP="$ROOT/root/app"
FRONT="$ROOT/frontend"
MODE="${1:-preview}"

say() { printf '[*] %s\n' "$*"; }

[ -x "$APP/.venv/bin/python" ] || { echo '[!] jalankan setup-local.sh dulu' >&2; exit 1; }
[ -d "$FRONT/node_modules" ] || { echo '[!] jalankan setup-local.sh dulu' >&2; exit 1; }

if [ -f "$ROOT/backend.pid" ] && kill -0 "$(cat "$ROOT/backend.pid")" 2>/dev/null; then
  say "backend sudah berjalan (pid $(cat "$ROOT/backend.pid"))"
else
  ( cd "$APP" && exec .venv/bin/python -m uvicorn backend.main:app \
      --host 127.0.0.1 --port 8000 ) > "$ROOT/backend.log" 2>&1 &
  echo $! > "$ROOT/backend.pid"
  say "backend start pid $(cat "$ROOT/backend.pid")"
fi

if [ "$MODE" = "--dev" ]; then
  script="dev"; port=5173; pidfile="$FRONT/_meta/dev.pid"
else
  script="preview"; port=4173; pidfile="$FRONT/_meta/preview.pid"
fi

if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
  say "frontend $script sudah berjalan (pid $(cat "$pidfile"))"
else
  ( cd "$FRONT" && exec npm run "$script" ) > "$FRONT/_meta/$script.log" 2>&1 &
  echo $! > "$pidfile"
  say "frontend $script start pid $(cat "$pidfile")"
fi

sleep 3
CURL_BIN="${CURL_BIN:-/usr/bin/curl}"
"$CURL_BIN" -q --noproxy '*' -sS -o /dev/null -w "[+] backend  http://127.0.0.1:8000/api/products -> %{http_code} (401 = butuh login, normal)\n" \
  http://127.0.0.1:8000/api/products || true
"$CURL_BIN" -q --noproxy '*' -sS -o /dev/null -w "[+] frontend http://127.0.0.1:$port/ -> %{http_code}\n" \
  "http://127.0.0.1:$port/" || true
printf '\nBuka http://127.0.0.1:%s/  (login: bejo / password123)\n' "$port"
printf 'Stop: %s/stop-local.sh\n' "$ROOT"
