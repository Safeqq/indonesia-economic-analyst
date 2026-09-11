# Indonesia Economic Intelligence

Project data analyst end-to-end menggunakan data resmi dari World Bank, BPS,
dan Bank Indonesia. Pipeline World Bank dan Bank Indonesia aktif; pipeline BPS
sudah tersedia dan memerlukan token pengguna untuk pengambilan produksi. Backend
FastAPI read-only menyediakan data mart, hasil forecast, dan status operasional.
Dashboard Next.js menyajikan tujuh ruang analisis responsif dengan filter global,
grafik interaktif, dan ekspor data yang sedang dilihat.

## Komponen

- MariaDB untuk penyimpanan dan analytical marts
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
make pipeline-bi  # mengambil BI-Rate dan JISDOR hingga bulan lengkap terakhir
make verify-bps  # memeriksa dua variabel dan cakupan 38 provinsi di database
make verify-bi  # memeriksa dua seri BI, periode, dan run produksi terbaru
make schema     # menerapkan penambahan schema secara idempotent
make marts      # membuat ulang staging dan analytical views
make quality    # menjalankan pemeriksaan kualitas dan freshness
make eda        # menjalankan lima notebook dan menyimpan salinan ber-output
make advanced-analytics  # mengevaluasi model dan membuat forecast jika gate lulus
make verify-analytics  # memeriksa holdout, quality gate, dan hasil forecast
make api        # menjalankan FastAPI pada http://127.0.0.1:8000
make dashboard  # menjalankan dashboard pada http://localhost:3000
make test       # menjalankan test Python dan frontend
make test-api   # menguji status, schema, input, dan empty state endpoint
make test-integration  # menguji query nyata dan idempotensi terhadap MariaDB
make frontend-check  # lint, typecheck, test, dan build dashboard
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

Pipeline Bank Indonesia tidak memerlukan API key. Pipeline mengunduh workbook
BI-Rate dan XML JISDOR resmi, menyimpan kedua respons secara utuh, lalu memuat
dua seri yang sejajar per bulan: BI-Rate yang berlaku pada akhir bulan dan
rata-rata JISDOR harian pada bulan tersebut.

```fish
make pipeline-bi
make marts
make verify-bi
```

Secara default, periode dimulai Agustus 2016 dan berakhir pada bulan kalender
terakhir yang sudah lengkap. Rentang lain harus memakai awal dan akhir bulan:

```fish
.venv/bin/python -m pipelines.jobs.run_bank_indonesia_pipeline \
  --start-date 2020-01-01 \
  --end-date 2025-12-31
```

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
Panduan notebook, metode analisis, dan lokasi hasil eksekusi tersedia di
`docs/eda.md`. Notebook sumber tetap bersih dari output; `make eda` menulis hasil
terbaru ke `data/exports/notebooks/` dan grafik PNG ke `data/exports/eda/`.
Forecasting tervalidasi, quality gate, deteksi anomali, dan tabel hasil dijelaskan
di `docs/advanced_analytics.md`.

Kontrak endpoint, parameter, pagination, dan contoh request tersedia di
`docs/api.md`. Setelah `make api`, buka `http://127.0.0.1:8000/docs` untuk mencoba
API melalui Swagger UI.

Jalankan `make api` dan `make dashboard` pada dua terminal untuk membuka
dashboard. Panduan halaman, filter, proxy API, dan ekspor tersedia di
`docs/dashboard.md`.

Project tidak menggunakan data dummy. Isi `data/raw` hanya berasal dari sumber
resmi; data buatan terbatas pada fixture test yang terisolasi.
