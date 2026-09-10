# Arsitektur

Alur World Bank yang sudah aktif:

```text
World Bank Indicators API v2
    ↓ HTTP GET dengan timeout, retry, dan user-agent
Snapshot JSON bertanggal di data/raw/world_bank
    ↓ normalisasi dan validasi
DataFrame dengan schema standar
    ↓ satu transaksi upsert
dim_source + dim_indicator + dim_region + dim_date
    ↓
fact_economic_indicator + status fact_pipeline_run
    ↓ view dengan grain terdokumentasi
stg_world_bank
    ↓
mart_national_overview + mart_indicator_trends + mart_asean_comparison
    ↓
quality checks blocking dan laporan freshness/gap
```

Natural key fakta adalah `indicator_id + region_id + source_id +
observation_date`. Run ulang memperbarui nilai dan `ingested_at`, sehingga tidak
menambah observasi duplikat. Jika validasi atau load gagal, transaksi fakta
dibatalkan dan `fact_pipeline_run` ditandai `failed` pada transaksi terpisah.

View dibangun ulang secara idempotent melalui `make marts`. `make quality`
menjalankan pemeriksaan natural key, mandatory field, rentang nilai, status
pipeline, freshness, dan periode yang hilang.

Alur BPS memakai model penyimpanan yang sama:

```text
BPS Web API + BPS_API_KEY
    ↓ domain provinsi + inventaris periode paginated + tabel dinamis
Snapshot JSON bertanggal di data/raw/bps (tanpa token)
    ↓ rekonsiliasi 38 kode wilayah + pemisahan seri turunan + validasi coverage
fact_economic_indicator + dim_indicator_metadata_history
    ↓
stg_bps → mart_regional_analysis → quality checks regional
```

Hash metadata menjaga versi nama, unit, definisi, dan catatan. Jika struktur key
`datacontent`, daftar domain, atau metadata wajib berubah, pipeline berhenti dengan
pesan schema drift sebelum fakta dimuat.

Analytics Python, endpoint data FastAPI, dan dashboard belum menjadi bagian alur
aktif. Komponen tersebut dibangun pada fase berikutnya setelah mart stabil.
