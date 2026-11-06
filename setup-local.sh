#!/usr/bin/env bash
# setup-local.sh - siapkan aplikasi lokal (venv, dependency, .env, data contoh, build).
# Aman dijalankan berulang: .env, DB, dan node_modules tidak ditimpa jika ada.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP="$ROOT/root/app"
FRONT="$ROOT/frontend"

say() { printf '[*] %s\n' "$*"; }
ok()  { printf '[+] %s\n' "$*"; }

command -v python3 >/dev/null || { echo '[!] python3 tidak ada' >&2; exit 1; }
command -v npm >/dev/null || { echo '[!] npm tidak ada' >&2; exit 1; }

mkdir -p "$APP/data" "$APP/backend/uploads"
chmod 700 "$APP/data" 2>/dev/null || true

if [ ! -f "$APP/.env" ]; then
  say "membuat $APP/.env (secret lokal acak)"
  secret="$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
  umask 077
  printf 'AUTH_TOKEN_SECRET=%s\n' "$secret" > "$APP/.env"
  printf 'AUTH_TOKEN_TTL_SECONDS=43200\n' >> "$APP/.env"
  printf 'DATABASE_URL=sqlite:///%s/data/shop.db\n' "$APP" >> "$APP/.env"
  printf 'FRONTEND_ORIGIN=http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173\n' >> "$APP/.env"
  chmod 600 "$APP/.env"
fi

if [ ! -x "$APP/.venv/bin/python" ]; then
  say "membuat venv backend"
  python3 -m venv --system-site-packages "$APP/.venv"
fi

say "memastikan dependency backend"
"$APP/.venv/bin/python" -m pip install -q -r "$APP/backend/requirements.txt"
"$APP/.venv/bin/python" -m pip install -q python-multipart

if [ ! -s "$APP/data/shop.db" ]; then
  say "seed database baseline"
  ( cd "$APP" && .venv/bin/python -m backend.init_db )
fi

if [ ! -d "$FRONT/node_modules" ]; then
  say "npm install frontend"
  ( cd "$FRONT" && npm install --no-audit --no-fund )
fi

say "build frontend"
( cd "$FRONT" && npm run build )

ok "setup selesai"
printf '\nJalankan:\n  %s/run-local.sh\n' "$ROOT"
printf 'Atau manual:\n'
printf '  cd %s && .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000\n' "$APP"
printf '  cd %s && npm run dev   # http://127.0.0.1:5173\n' "$FRONT"
printf '  cd %s && npm run preview  # http://127.0.0.1:4173 (hasil build)\n' "$FRONT"
