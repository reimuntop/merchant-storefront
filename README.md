# Merchant Storefront

Aplikasi toko online: katalog produk, keranjang, checkout, dan dasbor untuk penjual.
Backend dan frontend ada di satu repo dan jalan sepenuhnya di mesin sendiri.

Proyek ini dibuat untuk belajar dan demo lokal. Bukan untuk dipakai di produksi.

## Fitur

Pembeli
- katalog produk, pencarian, dan filter kategori
- keranjang, checkout, riwayat pembelian
- alamat pengiriman dan ulasan produk

Penjual
- kelola produk, kategori, stok, dan diskon
- pesanan masuk dengan catatan internal, ekspor pesanan
- ulasan pembeli dan analitik penjualan sederhana
- pengaturan toko, anggota tim (Viewer/Editor), dan akun

## Stack

- Backend: Python 3, FastAPI, SQLAlchemy, SQLite
- Frontend: Vue 3 + Vite

## Menjalankan

    ./setup-local.sh     # venv, dependency, .env, data contoh, build frontend
    ./run-local.sh       # backend :8000 + frontend preview :4173
    ./stop-local.sh      # hentikan

Buka http://127.0.0.1:4173/ lalu masuk dengan akun contoh **bejo / password123**.

Vite dev server (hot reload) di port 5173:

    ./run-local.sh --dev

Menjalankan manual:

    cd root/app && .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
    cd frontend && npm run dev      # atau: npm run preview

## Data

`root/app/data/shop.db` sudah berisi data contoh yang dibuat oleh
`root/app/backend/seed_db.py`: beberapa user, satu toko, enam produk, dan pesanan
contoh. Tidak ada data nyata di repo ini. Kalau mau mulai dari nol:

    rm root/app/data/shop.db && ./setup-local.sh

## Struktur

    root/app/backend/     source backend (FastAPI)
    root/app/data/        database SQLite + data contoh
    frontend/src/         source frontend (Vue 3)
    frontend/public/      aset statis
    setup-local.sh        setup awal
    run-local.sh          jalankan
    stop-local.sh         hentikan

## Konfigurasi

`root/app/.env` dibuat otomatis oleh `setup-local.sh`, isinya mengikuti
`.env.example`: `AUTH_TOKEN_SECRET`, `AUTH_TOKEN_TTL_SECONDS`, `DATABASE_URL`,
dan `FRONTEND_ORIGIN`.
