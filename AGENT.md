# Rencana Project: Indonesia Economic Intelligence

Dokumen ini adalah brief utama untuk AI code editor. Baca seluruh dokumen sebelum
mengubah kode. Kerjakan project secara bertahap, mulai dari audit repository dan
fase paling awal yang belum selesai. Jangan langsung mengimplementasikan semua
fase sekaligus.

## 1. Konteks pengguna

- Pengguna sedang belajar data analyst dari dasar.
- Database lokal menggunakan MariaDB 12.x di Arch Linux.
- Shell yang digunakan adalah Fish.
- Python yang terdeteksi pada komputer pengguna adalah Python 3.14.x.
- Pengguna membutuhkan penjelasan dalam Bahasa Indonesia yang sederhana.
- Project harus cukup advanced untuk portfolio data analyst.
- Project tidak boleh memakai data dummy sebagai data analisis atau dashboard.

## 2. Tujuan project

Bangun platform data analytics bernama **Indonesia Economic Intelligence** untuk
menganalisis kondisi ekonomi Indonesia dari sumber publik resmi. Project harus
menunjukkan alur kerja data analyst secara end-to-end:

1. Mengambil data dari sumber resmi.
2. Menyimpan data mentah tanpa perubahan.
3. Membersihkan dan memvalidasi data.
4. Memuat data ke MariaDB.
5. Membentuk analytical marts menggunakan SQL.
6. Melakukan exploratory dan statistical analysis.
7. Membuat forecasting yang dievaluasi secara benar.
8. Menyajikan hasil melalui API dan dashboard.
9. Memonitor kualitas serta freshness data.

Project harus menjawab pertanyaan berikut:

- Bagaimana tren GDP, inflasi, pengangguran, populasi, suku bunga, dan kurs?
- Bagaimana perubahan indikator secara year-over-year atau month-over-month?
- Bagaimana posisi Indonesia dibandingkan negara ASEAN?
- Provinsi mana yang mengalami pertumbuhan atau tekanan ekonomi paling besar?
- Indikator mana yang memiliki hubungan statistik dengan indikator lain?
- Apakah terdapat anomali atau perubahan tren?
- Seberapa baik model dapat memperkirakan periode berikutnya?

## 3. Aturan wajib untuk AI code editor

1. Audit isi repository sebelum menulis kode. Jangan menganggap semua file dalam
   rencana ini sudah tersedia.
2. Pertahankan perubahan pengguna dan jangan menghapus file yang tidak berkaitan.
3. Jangan membaca, menampilkan, menimpa, atau memasukkan `.env` ke Git.
4. Gunakan `.env.example` hanya sebagai template tanpa kredensial asli.
5. Jangan membuat data acak, fake records, seed observasi palsu, atau fallback
   dummy jika API gagal.
6. Jika sumber data gagal, hentikan pipeline dan catat error dengan jelas.
7. Data contoh hanya boleh digunakan sebagai fixture unit test dan tidak boleh
   masuk ke database produksi, notebook analisis, atau dashboard.
8. Simpan respons sumber apa adanya di `data/raw/<source>/` sebelum transformasi.
9. Setiap data harus memiliki sumber, periode, satuan, wilayah, dan waktu ingestion.
10. Gunakan transaksi database untuk proses load.
11. Gunakan upsert dan unique constraint agar pipeline idempotent.
12. Jangan menjalankan operasi database destruktif seperti `DROP DATABASE` atau
    `TRUNCATE` tanpa permintaan eksplisit pengguna.
13. Setiap perubahan harus diikuti lint, test, dan pemeriksaan yang relevan.
14. Jangan mengklaim berhasil jika perintah verifikasi belum dijalankan.
15. Kerjakan satu fase dalam satu waktu dan jelaskan file yang diubah.
16. Gunakan Bahasa Indonesia untuk dokumentasi pengguna dan pesan error utama.
17. Gunakan nama variabel/fungsi Python dalam Bahasa Inggris yang jelas.
18. Pastikan perintah aktivasi untuk Fish adalah:

    ```fish
    source .venv/bin/activate.fish
    ```

19. Bila aktivasi tidak diperlukan, gunakan `.venv/bin/python` secara langsung.
20. Pertahankan kompatibilitas MariaDB; jangan mengganti database ke PostgreSQL.

## 4. Sumber data nyata

### 4.1 World Bank Indicators API v2

- URL dasar: `https://api.worldbank.org/v2`
- Tidak memerlukan API key.
- Digunakan untuk indikator tahunan dan perbandingan ASEAN.
- Indikator awal:

| Kode | Nama | Frekuensi |
|---|---|---|
| `NY.GDP.MKTP.KD.ZG` | GDP growth | Tahunan |
| `FP.CPI.TOTL.ZG` | Inflation, consumer prices | Tahunan |
| `SL.UEM.TOTL.ZS` | Unemployment rate | Tahunan |
| `SP.POP.TOTL` | Population | Tahunan |
| `NY.GDP.PCAP.CD` | GDP per capita | Tahunan |

### 4.2 Badan Pusat Statistik

- Developer portal: `https://webapi.bps.go.id/developer`
- API key disimpan sebagai `BPS_API_KEY` di `.env`.
- Kandidat data: inflasi, kemiskinan, pengangguran, populasi, PDRB provinsi,
  indeks harga, dan indikator sosial ekonomi.
- AI harus memeriksa metadata API dan kode tabel/variabel resmi sebelum membuat
  connector. Jangan menebak endpoint.

### 4.3 Bank Indonesia

- Sumber resmi: `https://www.bi.go.id/id/statistik/default.aspx`
- Kandidat data: BI Rate, JISDOR/kurs, uang beredar, statistik sistem pembayaran,
  dan indikator moneter.
- AI harus mendokumentasikan URL tabel atau file, format, frekuensi, lisensi,
  serta aturan revisi sebelum mengimplementasikan parser.
- Jangan scraping halaman jika tersedia unduhan resmi yang lebih stabil.

## 5. Arsitektur

```text
Sumber resmi
    ↓
Python extraction
    ↓
Raw snapshot JSON/CSV
    ↓
Validation dan transformation
    ↓
MariaDB staging + dimensional model
    ↓
SQL analytical marts
    ↓
Python analytics dan forecasting
    ↓
FastAPI
    ↓
Dashboard Next.js
```

## 6. Stack teknologi

- Python 3.11+ dengan compatibility check untuk Python pengguna.
- MariaDB 12.x.
- SQLAlchemy 2.x dan PyMySQL.
- Pandas atau Polars untuk transformasi.
- Requests untuk HTTP client.
- PyYAML untuk konfigurasi indikator.
- Pytest untuk unit dan integration test.
- Ruff untuk lint dan formatting.
- Statsmodels dan Scikit-learn untuk analisis lanjutan.
- FastAPI untuk backend API.
- Next.js + TypeScript untuk frontend.
- ECharts atau Plotly untuk visualisasi interaktif.
- Jupyter untuk EDA yang dapat direproduksi.
- Makefile untuk perintah harian.

## 7. Struktur repository target

```text
indonesia-economic-intelligence/
├── .env.example
├── .gitignore
├── Makefile
├── README.md
├── requirements.txt
├── pyproject.toml
├── config/
│   ├── indicators.yml
│   ├── logging.yml
│   └── sources.yml
├── data/
│   ├── raw/
│   │   ├── world_bank/
│   │   ├── bps/
│   │   └── bank_indonesia/
│   ├── processed/
│   └── exports/
├── database/
│   ├── schema/
│   ├── migrations/
│   └── seeds/
├── pipelines/
│   ├── extract/
│   ├── transform/
│   ├── load/
│   ├── jobs/
│   └── utils/
├── sql/
│   ├── staging/
│   ├── marts/
│   ├── analysis/
│   └── quality/
├── notebooks/
├── analytics/
│   ├── descriptive/
│   ├── forecasting/
│   └── anomaly_detection/
├── backend/
│   ├── api/
│   ├── models/
│   ├── repositories/
│   └── services/
├── frontend/
├── scripts/
├── tests/
│   ├── pipeline/
│   ├── database/
│   ├── analytics/
│   └── api/
└── docs/
```

## 8. Model data MariaDB

### 8.1 Tabel dimensi

#### `dim_source`

- `source_id`
- `source_code`
- `source_name`
- `source_url`

#### `dim_indicator`

- `indicator_id`
- `indicator_code`
- `indicator_name`
- `unit`
- `frequency`

#### `dim_region`

- `region_id`
- `region_code`
- `region_name`
- `region_level`
- `parent_region_code`

#### `dim_date`

- `date_id`
- `full_date`
- `year`
- `quarter`
- `month`

### 8.2 Tabel fakta

#### `fact_economic_indicator`

- `observation_id`
- `indicator_id`
- `region_id`
- `source_id`
- `observation_date`
- `value`
- `ingested_at`

Unique key wajib:

```text
indicator_id + region_id + source_id + observation_date
```

#### `fact_pipeline_run`

- `run_id`
- `source_code`
- `started_at`
- `completed_at`
- `status`: `running`, `success`, atau `failed`
- `rows_loaded`
- `error_message`

### 8.3 Tabel lanjutan

Tambahkan saat fase terkait dimulai:

- `fact_forecast`
- `fact_data_quality`
- tabel staging per sumber
- tabel metadata dataset/revision bila dibutuhkan

Jangan menambahkan tabel tanpa use case dan query konsumennya.

## 9. Roadmap implementasi

### Fase 0 — Audit dan setup

### Tugas

- Periksa struktur repository dan status Git.
- Periksa `.env.example`, `.gitignore`, requirements, dan virtual environment.
- Pastikan MariaDB aktif.
- Pastikan `scripts/check_setup.py` dapat dijalankan langsung.
- Pastikan root project masuk ke `sys.path` ketika script dijalankan dari folder
  `scripts/`.
- Pastikan koneksi memakai SQLAlchemy `URL.create` agar password dengan karakter
  khusus aman.
- Pastikan Makefile memiliki target `setup`, `database`, `check`, `lint`, `test`,
  `pipeline`, dan `api`.

### Verifikasi

```fish
.venv/bin/python scripts/check_setup.py
make lint
make test
```

### Selesai jika

- Konfigurasi `.env` terbaca.
- MariaDB terhubung.
- Seluruh tabel awal tersedia.
- Lint bersih.
- Seluruh test lulus.

### Fase 1 — Pipeline World Bank

### Tugas

- Implementasikan HTTP client dengan timeout, retry, dan user-agent.
- Implementasikan parameter country, indicator, start year, dan end year.
- Validasi bentuk response `[metadata, records]`.
- Simpan raw snapshot beserta `retrieved_at`, source URL, country, indicator list,
  jumlah record, dan records asli.
- Transformasikan data menjadi schema standar.
- Validasi data kosong, null, duplikat, tanggal, frequency, dan finite number.
- Upsert `dim_source`, `dim_indicator`, `dim_region`, dan `dim_date`.
- Upsert `fact_economic_indicator` dalam transaksi.
- Catat pipeline run berhasil atau gagal.
- Sediakan CLI menggunakan `argparse`.

### Perintah target

```fish
make pipeline
```

atau:

```fish
.venv/bin/python -m pipelines.jobs.run_pipeline \
  --country IDN \
  --indicator NY.GDP.MKTP.KD.ZG \
  --start-year 2000 \
  --end-year 2025
```

### Test minimum

- Respons API valid dapat diekstrak.
- Rentang tahun tidak valid ditolak.
- Transformasi menghasilkan urutan dan tipe yang benar.
- Snapshot mempertahankan record sumber.
- Dataset kosong ditolak.
- Observasi duplikat ditolak.
- Upsert kedua tidak menambah duplicate fact.
- Pipeline gagal tercatat sebagai `failed`.

### Selesai jika

- Minimal empat indikator nyata berhasil masuk ke MariaDB.
- Raw snapshot tercipta.
- Menjalankan pipeline dua kali tidak menggandakan data.
- `fact_pipeline_run` mencatat status dan jumlah row.

### Fase 2 — Analytical SQL marts

### Tugas

Buat SQL staging dan marts berikut:

- `stg_world_bank.sql`
- `mart_national_overview.sql`
- `mart_indicator_trends.sql`
- `mart_asean_comparison.sql`
- `mart_regional_analysis.sql` setelah data BPS tersedia

Gunakan kemampuan SQL berikut secara nyata:

- `JOIN`
- `GROUP BY`
- CTE
- window function
- `LAG` dan `LEAD`
- rolling average
- year-over-year change
- ranking dan percentile
- conditional aggregation

### Quality queries

- Duplicate observation.
- Missing mandatory fields.
- Nilai di luar rentang logis.
- Freshness per source.
- Pipeline failure terbaru.
- Periode yang hilang di dalam time series.

### Selesai jika

- Setiap mart memiliki definisi grain yang jelas.
- Query dapat dijalankan ulang tanpa edit manual.
- Setiap mart memiliki minimal satu test kualitas.

### Fase 3 — Pipeline BPS

### Tugas

- Inventarisasi endpoint resmi dan metadata terlebih dahulu.
- Buat connector yang menggunakan `BPS_API_KEY`.
- Implementasikan pagination dan retry.
- Simpan respons mentah.
- Normalisasi kode wilayah BPS.
- Buat mapping provinsi yang terdokumentasi.
- Muat indikator regional ke model dimensi/fakta yang sama.
- Catat perubahan definisi atau unit antarperiode.

### Selesai jika

- Minimal dua indikator regional tersedia untuk seluruh provinsi yang didukung.
- Tidak ada wilayah tanpa kode resmi.
- Tidak ada observasi produksi dari data buatan.

### Fase 4 — Pipeline Bank Indonesia

### Tugas

- Pilih tabel resmi BI yang stabil.
- Dokumentasikan URL, format, sheet/table, unit, dan frekuensi.
- Implementasikan downloader dan parser terpisah.
- Tangani perubahan nama kolom secara eksplisit.
- Tambahkan validasi schema drift.
- Muat BI Rate dan minimal satu indikator kurs/moneter.

### Selesai jika

- Parser gagal dengan pesan jelas ketika format sumber berubah.
- Data BI dapat digabungkan dengan indikator tahunan/bulanan yang sesuai.

### Fase 5 — Exploratory Data Analysis

### Notebook

- `01_data_profiling.ipynb`
- `02_exploratory_analysis.ipynb`
- `03_correlation_analysis.ipynb`
- `04_regional_clustering.ipynb`
- `05_time_series_forecasting.ipynb`

### Aturan notebook

- Data dibaca dari MariaDB atau processed dataset yang dapat direproduksi.
- Jangan menanam hasil manual di dalam notebook.
- Gunakan fungsi reusable untuk proses yang dipakai lebih dari sekali.
- Tuliskan pertanyaan, metode, hasil, interpretasi, dan keterbatasan.
- Setiap insight harus menyebut periode dan sumber.
- Korelasi tidak boleh disebut sebagai kausalitas.

### Analisis minimum

- Statistik deskriptif.
- Missing value profile.
- Trend dan seasonality.
- Growth rate.
- Outlier detection.
- Correlation matrix.
- Lagged correlation.
- Perbandingan ASEAN.
- Segmentasi atau clustering regional setelah data BPS tersedia.

### Fase 6 — Advanced analytics

### Forecasting

- Buat seasonal-naive atau naive baseline.
- Gunakan time-based train/test split.
- Bandingkan baseline dengan ARIMA/SARIMA dan model lain hanya bila relevan.
- Gunakan MAE, RMSE, dan MAPE dengan perlakuan aman untuk nilai nol.
- Tampilkan confidence interval.
- Simpan model metadata dan hasil evaluasi.
- Jangan menampilkan forecast sebagai fakta.

### Anomaly detection

- Implementasikan metode statistik yang dapat dijelaskan terlebih dahulu.
- Simpan alasan sebuah titik dianggap anomali.
- Bedakan missing value, revisi sumber, dan anomali ekonomi.

### Selesai jika

- Model selalu dibandingkan dengan baseline.
- Evaluasi memakai data out-of-sample.
- Forecast tidak ditampilkan jika kualitasnya di bawah threshold yang ditetapkan.

### Fase 7 — FastAPI backend

### Endpoint target

- `GET /health`
- `GET /api/v1/overview`
- `GET /api/v1/indicators`
- `GET /api/v1/indicators/{code}/series`
- `GET /api/v1/regions`
- `GET /api/v1/regions/{code}/overview`
- `GET /api/v1/asean/comparison`
- `GET /api/v1/forecasts/{indicator_code}`
- `GET /api/v1/data-quality`
- `GET /api/v1/pipeline-runs`

### Aturan API

- Gunakan response schema Pydantic.
- Validasi parameter tahun, kode wilayah, dan kode indikator.
- Gunakan repository/service separation.
- Jangan meletakkan SQL mentah di route handler.
- Tambahkan pagination jika respons dapat besar.
- Tambahkan test untuk status code, schema, empty result, dan invalid input.

### Fase 8 — Dashboard Next.js

### Halaman target

1. Executive Overview.
2. Trend Explorer.
3. Regional Analysis.
4. ASEAN Benchmark.
5. Correlation & Drivers.
6. Forecasting Lab.
7. Data Quality Center.

### Fitur wajib

- Global filter untuk periode, indikator, wilayah, dan negara.
- KPI dengan nilai terbaru, perubahan, periode, dan sumber.
- Line chart time series.
- Comparison chart.
- Scatter plot.
- Correlation heatmap.
- Choropleth hanya setelah mapping wilayah tervalidasi.
- Tooltip dengan unit dan periode.
- Loading, empty, dan error states.
- Timestamp pembaruan terakhir.
- Export CSV untuk data yang sedang dilihat.
- Tampilan desktop dan mobile.

Dashboard tidak boleh menampilkan angka hardcoded sebagai data produksi.

### Fase 9 — Automation dan production readiness

### Tugas

- Jadwalkan pipeline berdasarkan frekuensi sumber.
- Tambahkan structured logging.
- Tambahkan retry yang tidak menyebabkan duplikasi.
- Tambahkan migration strategy.
- Tambahkan integration test MariaDB.
- Tambahkan API test dan frontend smoke test.
- Tambahkan data freshness alert.
- Lengkapi README, data dictionary, architecture, methodology, dan limitations.
- Siapkan deployment setelah pipeline dan dashboard stabil.

## 10. Urutan prioritas

AI code editor harus mengikuti urutan ini:

1. Audit repository dan jalankan test yang sudah ada.
2. Perbaiki setup sampai stabil.
3. Selesaikan World Bank pipeline.
4. Verifikasi data aktual di MariaDB.
5. Buat SQL marts nasional dan ASEAN.
6. Tambahkan BPS.
7. Tambahkan Bank Indonesia.
8. Lakukan EDA.
9. Implementasikan advanced analytics.
10. Bangun FastAPI.
11. Bangun dashboard.
12. Tambahkan automation dan deployment.

Jangan memulai frontend sebelum data model dan minimal satu mart stabil.

## 11. Workflow setiap tugas

Untuk setiap permintaan pengguna, AI harus:

1. Menyatakan fase dan tujuan kecil yang sedang dikerjakan.
2. Membaca file terkait sebelum mengubahnya.
3. Membuat perubahan sekecil mungkin tetapi lengkap.
4. Menambahkan atau memperbarui test.
5. Menjalankan:

   ```fish
   make lint
   make test
   ```

6. Menjalankan pemeriksaan spesifik fitur.
7. Menjelaskan hasil, file yang berubah, dan perintah pengguna berikutnya.
8. Berhenti setelah satu milestone logis agar pengguna dapat mencoba sendiri.

## 12. Perintah operasional

```fish
# Aktivasi environment
source .venv/bin/activate.fish

# Pemeriksaan setup
.venv/bin/python scripts/check_setup.py

# Lint
make lint

# Unit test
make test

# Pipeline data
make pipeline

# API
make api
```

Login MariaDB:

```fish
mariadb -u analyst -p economic_intelligence
```

## 13. Definition of Done project

Project baru dianggap selesai jika:

- Semua grafik menggunakan data publik nyata.
- Minimal tiga sumber resmi berhasil diintegrasikan.
- Pipeline dapat dijalankan ulang tanpa membuat duplikasi.
- Raw snapshot dan metadata sumber tersedia.
- Data memiliki source, unit, period, region, dan ingestion timestamp.
- Data-quality checks berjalan otomatis.
- SQL marts memiliki grain dan dokumentasi jelas.
- Insight dapat direproduksi dari SQL atau notebook.
- Forecast dibandingkan dengan baseline dan diuji out-of-sample.
- API memiliki schema dan test.
- Dashboard memiliki loading, empty, dan error states.
- Tidak ada secret atau `.env` di repository.
- README memungkinkan orang lain menjalankan project dari awal.
- Lint dan seluruh automated test lulus.

## 14. Instruksi pertama untuk AI code editor

Gunakan prompt berikut setelah melampirkan dokumen ini:

> Baca `RENCANA_PROJECT_DATA_ANALYST.md` seluruhnya. Audit repository saat ini,
> bandingkan dengan roadmap, lalu laporkan fase terakhir yang benar-benar sudah
> selesai berdasarkan bukti file dan hasil test. Setelah itu kerjakan hanya satu
> milestone berikutnya. Jangan memakai data dummy, jangan menimpa `.env`, dan
> jangan memulai frontend sebelum pipeline serta analytical mart stabil. Jelaskan
> setiap perubahan dalam Bahasa Indonesia dan jalankan seluruh verifikasi yang
> relevan sebelum menyatakan selesai.
