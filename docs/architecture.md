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

Alur Bank Indonesia aktif tanpa API key:

```text
Form unduhan XLSX BI-Rate + web-service XML JISDOR
    ↓ downloader terpisah dengan timeout/retry
Snapshot byte-for-byte + manifest SHA-256 di data/raw/bank_indonesia
    ↓ parser OpenXML/XML + validasi schema drift
Posisi BI-Rate akhir bulan + rata-rata JISDOR bulanan
    ↓ validasi rentang, periode lengkap, dan coverage dua seri
fact_economic_indicator
    ↓
stg_bank_indonesia → mart_monetary_conditions → quality checks BI
```

Transform hanya memuat bulan kalender lengkap. Kedua seri memakai tanggal pertama
bulan sehingga dapat di-join langsung, sedangkan `observation_year` mendukung
penggabungan dengan indikator tahunan.

Lapisan analytics Python kini aktif di atas empat mart:

```text
mart nasional + ASEAN + moneter + regional
    ↓ loader bersama dan fungsi analitik reusable
Lima notebook sumber tanpa output
    ↓ make eda / eksekusi kernel .venv
Notebook ber-output + grafik PNG di data/exports
    ↓
Insight tervalidasi di docs/insights.md
```

Loader mempertahankan tanggal dan metadata sumber dari mart. Notebook regional
tetap dapat dieksekusi saat BPS kosong, tetapi tidak menghasilkan cluster sampai
coverage minimum tersedia.

Lapisan advanced analytics memakai mart moneter yang sama:

```text
mart_monetary_conditions (JISDOR bulanan)
    ↓ validasi kalender tanpa imputasi
Baseline naïve + ARIMA/SARIMA dengan holdout berdasarkan waktu
    ↓ MAE/RMSE/MAPE + cakupan interval + quality gate
fact_forecast_run
    ├─ gate lulus → fact_forecast (estimasi + interval 95%)
    └─ gate gagal → evaluasi dan alasan saja
    ↓
Deteksi rolling MAD → fact_anomaly_event (tipe + alasan)
    ↓
JSON metadata + PNG di data/exports/advanced_analytics
```

Fingerprint data dan konfigurasi menjadi natural key run sehingga eksekusi ulang
tidak membuat duplikasi. Metadata evaluasi menyimpan setiap prediksi holdout dan
versi library. Endpoint data FastAPI dan dashboard dibangun pada fase berikutnya.
