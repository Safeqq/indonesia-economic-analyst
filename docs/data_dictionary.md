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
