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
versi library.

Lapisan FastAPI menggunakan pemisahan route, service, dan repository:

```text
HTTP request + validasi Pydantic
    ↓ backend/api
Aturan hasil kosong, pagination, dan keamanan forecast
    ↓ backend/services
SQL berparameter dan koneksi SQLAlchemy
    ↓ backend/repositories
MariaDB dimensions + facts + marts + quality queries
```

Semua endpoint bersifat read-only. Error database diubah menjadi respons 503
tanpa membocorkan exception internal, sedangkan pelanggaran invariant data
menghasilkan 500. Schema OpenAPI berasal dari response model Pydantic. Dashboard
Next.js menjadi konsumen read-only melalui rewrite `/backend/*`, sehingga alamat
FastAPI tetap berada di sisi server Next.js dan browser tidak memerlukan CORS.

```text
Browser desktop/mobile
    ↓ global filters + client-side loading/error/empty state
Next.js App Router
    ↓ rewrite /backend/*
FastAPI /api/v1
    ↓ response schema tervalidasi
ECharts + KPI + tabel + export CSV
```

Katalog indikator dan wilayah selalu berasal dari API. Perhitungan perubahan,
korelasi Pearson, dan penyelarasan tanggal dilakukan dari observasi yang sedang
dilihat. Dashboard tidak menyimpan angka observasi produksi di source code.

Lapisan operasional menjalankan sumber sesuai frekuensinya:

```text
systemd timer harian / container automation satu kali
    ↓ config/automation.yml + riwayat run sukses
keputusan due per sumber
    ↓ named lock MariaDB
pipeline sumber + bounded retry untuk error sementara
    ↓ upsert fakta + pipeline_schedule_run
rebuild marts → blocking quality checks → advanced analytics bila BI berubah
    ↓
freshness thresholds → JSON log + exit code + data_freshness_alert
```

World Bank dan BPS memakai jadwal tahunan, sedangkan Bank Indonesia memakai jadwal
bulanan. Retry menjalankan kembali operasi dengan natural key yang sama; unique
constraint fakta mencegah penambahan observasi duplikat. Validation error tidak
dicoba ulang karena biasanya menunjukkan perubahan kontrak sumber yang perlu
ditinjau.

Perubahan database setelah baseline memakai migration maju berurutan. Runner
mengambil named lock khusus, memverifikasi checksum semua versi yang sudah
tercatat, menerapkan versi baru, lalu menulis `schema_migration`. File migration
yang sudah diterapkan tidak boleh diedit. Koneksi SQL menetapkan session timezone
UTC agar timestamp ingestion, pipeline, alert, dan model konsisten antar-host.

Deployment satu host memisahkan empat tanggung jawab:

```text
Browser → dashboard Next.js standalone → API FastAPI → MariaDB
                                          ↑
                      migration one-shot + automation one-shot
```

Database hanya tersedia di jaringan internal Compose. API dan dashboard memiliki
healthcheck; dashboard baru dimulai setelah API sehat, dan API baru dimulai
setelah migration selesai. TLS dan pembatasan trafik ditempatkan pada reverse
proxy di depan service.
