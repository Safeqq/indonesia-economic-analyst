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
```

Natural key fakta adalah `indicator_id + region_id + source_id +
observation_date`. Run ulang memperbarui nilai dan `ingested_at`, sehingga tidak
menambah observasi duplikat. Jika validasi atau load gagal, transaksi fakta
dibatalkan dan `fact_pipeline_run` ditandai `failed` pada transaksi terpisah.

Analytical marts, analytics Python, endpoint data FastAPI, dan dashboard belum
menjadi bagian alur aktif. Komponen tersebut dibangun setelah pipeline data dan
mart terkait stabil.
