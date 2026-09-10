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

- Status: aktif.
- Portal statistik: <https://www.bi.go.id/id/statistik/default.aspx>.
- Autentikasi: tidak memerlukan API key.
- Tanggal verifikasi sumber dan format: 10 September 2026.

### BI-Rate

| Properti | Nilai |
|---|---|
| Halaman resmi | <https://www.bi.go.id/id/statistik/indikator/bi-rate.aspx> |
| Metode unduh | HTTP POST pada tombol `Unduh` setelah mengambil state form halaman |
| Format/file | XLSX, nama respons `BI-7Day-RR.xlsx` |
| Sheet diterima | `BI-7Day-RR`; alias eksplisit `BI-Rate` |
| Kolom tanggal | `Tanggal`; alias eksplisit `Periode` |
| Kolom nilai | `BI-7Day-RR`; alias eksplisit `BI-Rate` |
| Satuan sumber | persen |
| Frekuensi sumber | tanggal keputusan kebijakan |
| Seri yang dimuat | posisi BI-Rate yang berlaku pada akhir bulan |

BI 7-Day Reverse Repo Rate mulai dipakai sebagai suku bunga kebijakan pada
19 Agustus 2016. Sejak 21 Desember 2023, Bank Indonesia memakai nama BI-Rate
tanpa mengubah makna, tujuan, atau operasionalisasi instrumennya. Karena itu,
periode produksi default dimulai Agustus 2016 dan dua nama tersebut diperlakukan
sebagai satu seri kebijakan yang berkesinambungan. Referensi resmi:
<https://www.bi.go.id/id/fungsi-utama/moneter/bi-rate/default.aspx>.

Untuk setiap bulan, transform memilih keputusan terakhir dengan tanggal efektif
pada atau sebelum akhir bulan. Nilai disimpan pada tanggal pertama bulan dengan
kode `BI.POLICY_RATE.MONTHLY`, frekuensi `monthly`, dan unit `percent`.

### JISDOR USD/IDR

| Properti | Nilai |
|---|---|
| Halaman resmi | <https://www.bi.go.id/id/statistik/informasi-kurs/jisdor/default.aspx> |
| Web-service resmi | <https://www.bi.go.id/biwebservice/wskursbi.asmx/getSubKursJisdor3> |
| Parameter | `mts=USD`, `startDate=YYYY-MM-DD`, `endDate=YYYY-MM-DD` |
| Format | XML `DataSet` |
| Tabel/record | `Table` di dalam `NewDataSet` |
| Kolom tanggal | `tgl_subkursasing` |
| Kolom nilai | `beli_subkursasing` dan `jual_subkursasing`; keduanya wajib sama |
| Kolom mata uang | `mts_subkursasing`, wajib `USD` |
| Denominasi | `nil_subkursasing`, wajib `1` |
| Satuan sumber | rupiah per 1 USD |
| Frekuensi sumber | harian pada hari kerja |
| Seri yang dimuat | rata-rata aritmetika nilai harian per bulan |

JISDOR adalah harga spot USD/IDR yang dihitung BI dari transaksi valuta asing
antarbank. BI menyatakan data diterbitkan pada setiap hari kerja. Nilai bulanan
disimpan pada tanggal pertama bulan dengan kode
`BI.JISDOR.USD_IDR.MONTHLY_AVG`, frekuensi `monthly`, dan unit `IDR per USD`.
Transform tidak mengisi hari libur dan tidak memasukkan bulan berjalan yang
belum lengkap.

Setiap run menyimpan byte workbook XLSX dan XML persis seperti respons sumber.
Manifest JSON mencatat URL, metode, parameter, content type, ukuran, nama file,
dan checksum SHA-256. Parser menerima nama sheet/kolom dan field XML yang
tercantum di `config/bank_indonesia.yml`. Perubahan di luar alias itu menghasilkan
error schema drift sebelum fakta dimuat. Run ulang melakukan upsert pada natural
key, sehingga revisi BI mengganti nilai lama tanpa menambah duplikat.
