# Indonesia Economic Intelligence

Project data analyst end-to-end menggunakan data resmi dari World Bank, BPS,
dan Bank Indonesia. Pipeline World Bank aktif; pipeline BPS sudah tersedia dan
memerlukan token pengguna untuk pengambilan produksi.

## Komponen

- MySQL untuk penyimpanan dan analytical marts
- Python untuk proses extract, transform, dan load
- FastAPI untuk data service
- Next.js untuk dashboard interaktif
- Notebook untuk EDA, korelasi, segmentasi, dan forecasting

## Setup lokal (Arch Linux + MariaDB + Fish)

```bash
chmod +x scripts/setup_project.sh scripts/init_database.sh
./scripts/setup_project.sh
```

Setelah itu, ubah password pada `.env`, lalu siapkan database:

```bash
./scripts/init_database.sh
source .venv/bin/activate.fish
.venv/bin/python scripts/check_setup.py
```

Panduan lengkap tersedia di `docs/setup.md`.

## Menjalankan komponen

```bash
make pipeline   # mengambil lima indikator World Bank untuk Indonesia, 2000–2025
make pipeline-bps  # mengambil dua tabel regional BPS; perlu BPS_API_KEY
make verify-bps  # memeriksa dua variabel dan cakupan 38 provinsi di database
make schema     # menerapkan penambahan schema secara idempotent
make marts      # membuat ulang staging dan analytical views
make quality    # menjalankan pemeriksaan kualitas dan freshness
make api        # menjalankan FastAPI pada http://127.0.0.1:8000
make test       # menjalankan unit test
make test-integration  # menguji idempotensi dengan tabel sementara MariaDB
```

Rentang dan indikator dapat dipilih melalui CLI:

```fish
.venv/bin/python -m pipelines.jobs.run_pipeline \
  --country IDN \
  --indicator NY.GDP.MKTP.KD.ZG \
  --start-year 2000 \
  --end-year 2025
```

Opsi `--indicator` dapat diulang. Tanpa opsi tersebut, pipeline mengambil semua
indikator World Bank dalam `config/indicators.yml`. Setiap run menyimpan respons
API utuh beserta metadata pengambilan di `data/raw/world_bank/`, kemudian
melakukan upsert transaksional ke model dimensi dan fakta MariaDB.

Pipeline BPS mengambil variabel resmi `1975` (jumlah penduduk pertengahan tahun)
dan `543` (tingkat pengangguran terbuka menurut provinsi):

```fish
make pipeline-bps
```

Setiap run merekonsiliasi `config/bps_provinces.yml` dengan endpoint domain BPS,
mengambil seluruh halaman inventaris periode, lalu menyimpan respons utuh di
`data/raw/bps/`. API key hanya dipakai pada request dan tidak ditulis ke snapshot.
Nama, unit, definisi, catatan, serta ID seri turunan berasal dari metadata API.

Untuk mengisi benchmark 11 negara ASEAN dari Fish:

```fish
for country in BRN KHM IDN LAO MYS MMR PHL SGP THA TLS VNM
    .venv/bin/python -m pipelines.jobs.run_pipeline \
      --country $country --start-year 2000 --end-year 2025
end

make marts
make quality
```

Definisi grain, metrik, dan interpretasi mart tersedia di `docs/marts.md`.

Project tidak menggunakan data dummy. Isi `data/raw` hanya berasal dari sumber
resmi; data buatan terbatas pada fixture test yang terisolasi.
