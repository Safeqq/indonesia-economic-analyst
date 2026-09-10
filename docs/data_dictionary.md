# Kamus Data

## Schema standar pipeline

Satu baris mewakili satu observasi indikator untuk satu wilayah, satu sumber,
dan satu tanggal.

| Kolom | Tipe logis | Keterangan |
|---|---|---|
| `indicator_code` | string | Kode indikator resmi sumber |
| `indicator_name` | string | Nama indikator yang dapat dibaca manusia |
| `unit` | string | Satuan nilai |
| `frequency` | enum | `daily`, `monthly`, `quarterly`, atau `annual` |
| `region_code` | string | Kode resmi negara atau wilayah |
| `region_name` | string | Nama negara atau wilayah |
| `region_level` | enum | `country`, `province`, atau `city` |
| `observation_date` | date | Awal periode; indikator tahunan memakai 1 Januari |
| `value` | numeric | Nilai observasi finite |
| `source_code` | string | Kode unik sumber data |
| `source_name` | string | Nama sumber data |
| `source_url` | string | URL dasar sumber |
| `retrieved_at` | datetime UTC | Waktu respons sumber diambil |

## `dim_source`

Grain: satu baris per sumber data. `source_code` bersifat unik.

## `dim_indicator`

Grain: satu baris per indikator. Menyimpan nama, satuan, dan frekuensi.
`indicator_code` bersifat unik.

## `dim_region`

Grain: satu baris per wilayah resmi. Data World Bank saat ini memakai level
`country`. `region_code` bersifat unik.

Data BPS memakai kode domain provinsi empat digit, `region_level = province`, dan
`parent_region_code = IDN`. Daftar kode dikonfirmasi ulang melalui API setiap run.

## `dim_date`

Grain: satu baris per tanggal observasi. `date_id` memakai format integer
`YYYYMMDD`.

## `fact_economic_indicator`

Grain: satu observasi untuk kombinasi indikator, wilayah, sumber, dan tanggal.
Kombinasi tersebut memiliki unique constraint. `ingested_at` diperbarui ketika
sumber merevisi atau pipeline memuat ulang observasi.

## `fact_pipeline_run`

Grain: satu eksekusi pipeline. Status dimulai sebagai `running`, lalu diselesaikan
sebagai `success` atau `failed`. Run sukses menyimpan jumlah observasi yang
diproses; run gagal menyimpan pesan error dan tidak memuat fakta parsial.

## Snapshot mentah World Bank

Setiap file `data/raw/world_bank/world_bank_<country>_<timestamp>.json` berisi
kode dan URL sumber, waktu retrieval UTC, negara, daftar indikator, jumlah record,
parameter request, serta payload `[metadata, records]` persis dari setiap request.

## Snapshot mentah BPS

Setiap file `data/raw/bps/bps_<timestamp>.json` berisi respons domain provinsi,
seluruh halaman inventaris periode, dan payload tabel dinamis persis dari BPS.
URL serta parameter publik dicatat, sedangkan `BPS_API_KEY` tidak disimpan.

## Snapshot mentah Bank Indonesia

Setiap run membuat tiga file bertimestamp di `data/raw/bank_indonesia`: workbook
BI-Rate `.xlsx`, respons web-service JISDOR `.xml`, dan manifest `.json`. Dua file
sumber disimpan byte-for-byte. Manifest mencatat request publik dan checksum
SHA-256 untuk memeriksa integritas snapshot.

## `dim_indicator_metadata_history`

Grain: satu versi metadata untuk satu indikator dan sumber. Hash SHA-256 meliputi
nama, unit, definisi, catatan, ID variabel, ID turunan variabel, dan ID turunan
periode. `period_start`/`period_end` menunjukkan rentang observasi yang memakai
versi tersebut; `first_observed_at`/`last_observed_at` menunjukkan kapan pipeline
melihatnya.

## `stg_world_bank`

Grain: satu indikator, negara, sumber, dan tanggal observasi. View menyatukan
natural key, metadata dimensi, nilai, periode, dan waktu ingestion.

## `mart_national_overview`

Grain: satu tahun untuk Indonesia. Lima indikator disajikan sebagai kolom KPI;
`indicator_coverage` mencatat kelengkapan indikator per tahun.

## `mart_indicator_trends`

Grain: satu indikator, negara, dan tanggal. Menyediakan nilai periode sebelum dan
sesudah, rolling average tiga periode, serta perubahan year-over-year.

## `mart_asean_comparison`

Grain: satu indikator, anggota ASEAN saat ini, dan tanggal. Menyediakan rata-rata,
selisih dari rata-rata, coverage negara, rank, percentile, dan status keanggotaan
pada tanggal observasi. Definisi lengkap tersedia di `docs/marts.md`.

## `stg_bps`

Grain: satu seri BPS, provinsi, sumber, dan tanggal observasi. Kode seri memuat ID
`var`, `turvar`, serta `turtahun` resmi agar kategori tidak tercampur.

## `mart_regional_analysis`

Grain: satu seri BPS, provinsi, dan tanggal. Menyediakan perubahan tahunan,
rata-rata provinsi yang tersedia, selisih dari rata-rata, coverage, rank, dan
percentile.

## `stg_bank_indonesia`

Grain: satu indikator BI bulanan, negara, sumber, dan tanggal observasi. Saat ini
berisi posisi BI-Rate akhir bulan dan rata-rata JISDOR harian per bulan untuk
Indonesia (`IDN`). `observation_date` selalu tanggal pertama bulan.

## `mart_monetary_conditions`

Grain: satu bulan kalender untuk Indonesia. Mart menggabungkan BI-Rate dan
JISDOR sebagai kolom, lalu menyediakan perubahan BI-Rate dalam poin persentase,
perubahan JISDOR bulanan, persentase perubahan JISDOR, rata-rata berjalan tiga
bulan, dan jumlah seri yang tersedia.
