# Setup Project di Arch Linux

## 1. Prasyarat

Pastikan MariaDB aktif:

```bash
systemctl status mariadb --no-pager
```

Pasang paket sistem bila belum tersedia:

```bash
sudo pacman -S --needed python python-pip mariadb git make
```

## 2. Setup environment Python

Dari root project:

```bash
chmod +x scripts/setup_project.sh scripts/init_database.sh
./scripts/setup_project.sh
```

Script akan membuat virtual environment `.venv`, memasang dependensi, dan
menyalin `.env.example` menjadi `.env` tanpa menimpa konfigurasi yang sudah ada.

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
Setelah menarik perubahan schema baru, jalankan `make schema`; perintah ini hanya
menjalankan `CREATE ... IF NOT EXISTS` melalui user aplikasi.

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
make api
```
