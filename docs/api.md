# FastAPI Backend

Fase 7 menyediakan API read-only di atas dimensi, fakta, analytical mart,
quality checks, dan hasil advanced analytics MariaDB. Route handler tidak memuat
SQL; akses data berada di repository dan aturan respons berada di service.

## Menjalankan API

Aktifkan MariaDB dan pastikan `.env` sudah benar, lalu jalankan:

```fish
make check
make api
```

Server lokal tersedia di `http://127.0.0.1:8000`. Dokumentasi OpenAPI interaktif
tersedia di `/docs`, alternatif dokumentasinya di `/redoc`, dan schema mentahnya
di `/openapi.json`.

## Endpoint

| Endpoint | Fungsi | Parameter utama |
|---|---|---|
| `GET /health` | Kesiapan aplikasi dan koneksi database | - |
| `GET /api/v1/overview` | Snapshot nasional dan moneter terbaru | - |
| `GET /api/v1/indicators` | Katalog indikator | `frequency`, `source_code`, pagination |
| `GET /api/v1/indicators/{code}/series` | Observasi indikator per wilayah | `region_code`, `start_year`, `end_year`, pagination |
| `GET /api/v1/regions` | Katalog negara/provinsi/kota | `region_level`, pagination |
| `GET /api/v1/regions/{code}/overview` | Nilai terbaru setiap indikator wilayah | `year`, pagination |
| `GET /api/v1/asean/comparison` | Perbandingan lintas negara ASEAN | `indicator_code`, `year` |
| `GET /api/v1/forecasts/{indicator_code}` | Run forecast terbaru dan estimasinya | `region_code` |
| `GET /api/v1/data-quality` | Ringkasan semua quality query | - |
| `GET /api/v1/pipeline-runs` | Riwayat eksekusi pipeline | `source_code`, `status`, pagination |

`indicator_code` wajib untuk perbandingan ASEAN. Jika `year` tidak diberikan,
API memilih tahun terbaru yang tersedia untuk indikator tersebut. Seri indikator
memakai `IDN` sebagai wilayah default.

## Pagination dan hasil kosong

Endpoint yang berpotensi besar menerima `page` mulai dari 1 dan `page_size`
antara 1–100. Respons memuat:

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 0,
    "total_pages": 0
  }
}
```

Filter yang valid tetapi tidak memiliki observasi mengembalikan HTTP 200 dengan
`items` kosong. Kode indikator atau wilayah yang tidak dikenal mengembalikan 404.
Format kode, rentang tahun, urutan `start_year`/`end_year`, enum, dan pagination
yang tidak valid mengembalikan 422.

## Aturan forecast

Endpoint forecast selalu menyertakan status quality gate, metrik model dan
baseline, threshold, periode evaluasi, serta `is_estimate_not_fact: true`. Baris
estimasi hanya dibaca dari `fact_forecast` dengan `is_publishable = 1`. Jika run
terbaru gagal quality gate, API mengembalikan alasan dan `items: []`, meskipun
terdapat data anak yang tidak konsisten.

Service juga memeriksa jumlah estimasi terhadap horizon, tanggal terhadap batas
data, dan posisi point forecast di dalam interval. Pelanggaran invariant tersebut
tidak diteruskan sebagai angka ke pengguna.

## Error dan keamanan data

- 404: resource tidak tersedia;
- 422: parameter tidak memenuhi schema;
- 500: data tersimpan melanggar kontrak API;
- 503: database tidak dapat diakses.

Respons 500/503 tidak memuat SQL, kredensial, atau pesan exception internal.
Endpoint pipeline hanya mengembalikan `has_error`; isi internal `error_message`
tidak diekspos.

## Contoh

```fish
curl 'http://127.0.0.1:8000/api/v1/indicators?page=1&page_size=20'

curl 'http://127.0.0.1:8000/api/v1/indicators/NY.GDP.MKTP.KD.ZG/series?region_code=IDN&start_year=2020&end_year=2025'

curl 'http://127.0.0.1:8000/api/v1/asean/comparison?indicator_code=NY.GDP.MKTP.KD.ZG&year=2025'

curl 'http://127.0.0.1:8000/api/v1/forecasts/BI.JISDOR.USD_IDR.MONTHLY_AVG'
```

Jalankan test route terisolasi dengan `make test-api`. Test database nyata ikut
dalam `make test-integration` ketika `RUN_DB_INTEGRATION=1` diaktifkan oleh target
Makefile.
