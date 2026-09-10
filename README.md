# Indonesia Economic Intelligence

Project data analyst end-to-end menggunakan data resmi dari World Bank, BPS,
dan Bank Indonesia. Integrasi yang aktif saat ini adalah pipeline World Bank.

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

Project tidak menggunakan data dummy. Isi `data/raw` hanya berasal dari sumber
resmi; data buatan terbatas pada fixture test yang terisolasi.
