# Setup Project di Arch Linux

## 1. Prasyarat

Pastikan MariaDB aktif:

```bash
systemctl status mariadb --no-pager
```

Pasang paket sistem bila belum tersedia. Dashboard memerlukan Node.js 20.9 atau
lebih baru:

```bash
sudo pacman -S --needed python python-pip mariadb git make nodejs npm chromium
```

Chromium dipakai oleh `make frontend-smoke` untuk membuka seluruh halaman pada
viewport desktop dan mobile. Lokasi browser lain dapat diberikan lewat
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`.

Deployment container juga memerlukan Docker Engine dan plugin Compose:

```bash
sudo pacman -S --needed docker docker-compose
```

## 2. Setup project

Dari root project:

```bash
chmod +x scripts/setup_project.sh scripts/init_database.sh
./scripts/setup_project.sh
```

Script akan membuat virtual environment `.venv`, memasang dependensi Python dan
frontend dari lockfile, lalu menyalin `.env.example` menjadi `.env` tanpa
menimpa konfigurasi yang sudah ada.

## 3. Atur konfigurasi

Buka `.env`, lalu ganti setidaknya:

```dotenv
MYSQL_PASSWORD=password_lokal_yang_kuat
```

Isi `BPS_API_KEY` dengan token dari portal developer BPS sebelum menjalankan
`make pipeline-bps`. Setup World Bank tetap dapat digunakan jika field ini kosong.
Pipeline Bank Indonesia tidak memerlukan API key.

## 4. Buat database dan user aplikasi

```bash
./scripts/init_database.sh
```

Script memakai autentikasi socket melalui `sudo mariadb`, membuat database,
user aplikasi lokal, dan tabel awal. Script tidak menghapus database yang ada.
Setelah menarik perubahan schema baru, jalankan `make schema`; perintah ini
menjalankan bootstrap idempotent dan migration forward-only melalui user aplikasi.

## 5. Verifikasi

```bash
source .venv/bin/activate.fish
python scripts/check_setup.py
make test
```

Jika seluruh pemeriksaan menampilkan `[OK]`, setup selesai. Tahap selanjutnya
adalah mengerjakan pipeline World Bank sebagai sumber data nyata pertama.

## Perintah harian

```bash
source .venv/bin/activate.fish
make check
make schema
make pipeline
make pipeline-bps
make pipeline-bi
make marts
make quality
make verify-bi
make eda
make advanced-analytics
make verify-analytics
make test-api
make api
make dashboard
make frontend-check
make frontend-smoke
```

Setelah `make api`, periksa `http://127.0.0.1:8000/health` dan buka dokumentasi
interaktif di `http://127.0.0.1:8000/docs`. API memerlukan MariaDB aktif karena
health check juga memeriksa koneksi database.

Dashboard berjalan di `http://localhost:3000` dan meneruskan request
`/backend/*` ke `http://127.0.0.1:8000` secara default. Untuk alamat API lain,
jalankan dashboard dengan environment variable, misalnya:

```fish
env API_BASE_URL=https://api.example.id make dashboard
```
