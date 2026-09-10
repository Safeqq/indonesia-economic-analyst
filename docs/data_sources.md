# Sumber Data

## World Bank Indicators API v2

- Status: aktif.
- URL dasar: <https://api.worldbank.org/v2>.
- Dokumentasi API: <https://datahelpdesk.worldbank.org/knowledgebase/articles/889392>.
- Struktur parameter: <https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures>.
- Autentikasi: tidak memerlukan API key.
- Format: JSON dengan bentuk `[metadata, records]`.
- Frekuensi indikator awal: tahunan.
- Tanggal akses implementasi: 9 September 2026.
- Lisensi: umumnya CC BY 4.0, kecuali metadata dataset atau indikator menyatakan
  ketentuan lain. Lihat <https://data.worldbank.org/summary-terms-of-use>.

Indikator aktif:

| Kode | Nama | Satuan |
|---|---|---|
| `NY.GDP.MKTP.KD.ZG` | GDP growth | percent |
| `FP.CPI.TOTL.ZG` | Inflation, consumer prices | percent |
| `SL.UEM.TOTL.ZS` | Unemployment rate | percent |
| `SP.POP.TOTL` | Population | people |
| `NY.GDP.PCAP.CD` | GDP per capita | current USD |

Nilai World Bank dapat direvisi ketika penyedia memperbarui seri. Setiap run
menyimpan payload API utuh sebagai snapshot bertanggal. Load menggunakan natural
key indikator, wilayah, sumber, dan tanggal observasi; nilai revisi menggantikan
nilai lama tanpa membuat fakta duplikat. `ingested_at` menunjukkan waktu snapshot
yang terakhir dimuat.

Untuk benchmark ASEAN, cakupan wilayah memakai 11 negara anggota saat ini sesuai
daftar ASEAN Secretariat: <https://asean.org/member-states/>. Data pembanding
terakhir diambil pada 10 September 2026 untuk periode 2000–2025.

## BPS Web API

- Status: pipeline tersedia; pengambilan produksi menunggu `BPS_API_KEY` lokal.
- Developer portal: <https://webapi.bps.go.id/developer>.
- Dokumentasi endpoint: <https://webapi.bps.go.id/documentation>.
- Autentikasi: `BPS_API_KEY`.
- Domain: `0000` (BPS pusat).
- Format: JSON tabel dinamis dengan dimensi `var`, `turvar`, `vervar`, `tahun`,
  `turtahun`, dan nilai dalam `datacontent`.
- Tanggal inventarisasi dokumentasi: 10 September 2026.

Variabel awal tercantum dalam katalog Special Data Dissemination Standard (SDDS)
pada dokumentasi resmi BPS:

| ID variabel | Nama resmi | Frekuensi model |
|---|---|---|
| `1975` | Jumlah Penduduk Pertengahan Tahun | tahunan |
| `543` | Tingkat Pengangguran Terbuka Menurut Provinsi | tahunan |

Endpoint yang digunakan:

| Tujuan | Pola endpoint |
|---|---|
| Domain provinsi | `/v1/api/domain/type/prov/key/<token>/` |
| Inventaris periode | `/v1/api/list/model/th/lang/ind/domain/0000/var/<id>/page/<n>/key/<token>/` |
| Data dan metadata | `/v1/api/list/model/data/lang/ind/domain/0000/var/<id>/key/<token>/` |

Mapping 38 provinsi berada di `config/bps_provinces.yml`. Kode dalam file itu
wajib sama dengan respons endpoint domain pada setiap run; perubahan cakupan
menghentikan pipeline agar wilayah tidak dipetakan berdasarkan tebakan. Agregat
Indonesia (`9999`) tidak dimuat sebagai provinsi.

Satu tabel BPS dapat memiliki beberapa `turvar` atau `turtahun`. Pipeline membuat
kode seri dari ID resmi tersebut agar observasi dengan definisi periode berbeda
tidak digabung. Respons mentah disimpan sebelum transform. API key tidak disimpan
di file snapshot.

Unit, definisi, dan catatan berasal dari objek metadata `var`. Setiap kombinasi
metadata di-hash dan disimpan di `dim_indicator_metadata_history` bersama rentang
periode serta waktu pertama/terakhir terlihat. Perubahan metadata menghasilkan
versi baru, sementara metadata lama tetap tersedia untuk audit.

## Bank Indonesia

- Status: tabel resmi belum dipilih.
- Portal statistik: <https://www.bi.go.id/id/statistik/default.aspx>.

URL unduhan, format, sheet, satuan, frekuensi, lisensi, dan aturan revisi harus
didokumentasikan sebelum parser dibuat. Pipeline produksi belum mengambil data
Bank Indonesia.
