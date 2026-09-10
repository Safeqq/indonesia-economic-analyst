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

## BPS Web API

- Status: connector dasar tersedia, endpoint statistik belum dipilih.
- Developer portal: <https://webapi.bps.go.id/developer>.
- Autentikasi: `BPS_API_KEY`.

Metadata variabel dan endpoint resmi harus diinventarisasi sebelum connector ini
diaktifkan. Pipeline produksi belum mengambil data BPS.

## Bank Indonesia

- Status: tabel resmi belum dipilih.
- Portal statistik: <https://www.bi.go.id/id/statistik/default.aspx>.

URL unduhan, format, sheet, satuan, frekuensi, lisensi, dan aturan revisi harus
didokumentasikan sebelum parser dibuat. Pipeline produksi belum mengambil data
Bank Indonesia.
