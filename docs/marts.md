# Analytical SQL Marts

Seluruh objek Fase 2 dibuat sebagai MariaDB view. Jalankan ulang definisinya
tanpa mengedit SQL:

```fish
make marts
make quality
```

`make quality` mengembalikan exit code nonzero jika pemeriksaan blocking
menemukan pelanggaran. Freshness dan missing period bersifat informasional agar
ketiadaan data resmi tidak diganti dengan nilai buatan.

## `stg_world_bank`

Grain: satu baris per indikator, negara, sumber, dan tanggal observasi.

View ini menggabungkan tabel fakta dengan dimensi indikator, wilayah, sumber,
dan tanggal. Kolom bisnis yang dipakai mart tersedia tanpa ID surrogate.

Quality test: `check_stg_world_bank_grain.sql`.

## `mart_national_overview`

Grain: satu baris per tahun untuk Indonesia (`IDN`).

Conditional aggregation mengubah lima indikator menjadi kolom KPI: GDP growth,
inflasi, pengangguran, populasi, dan GDP per kapita. `indicator_coverage`
menunjukkan jumlah indikator yang tersedia pada tahun tersebut; nilainya tidak
diisi secara manual ketika sumber tidak menyediakan observasi.

Quality test: `check_mart_national_overview_grain.sql`.

## `mart_indicator_trends`

Grain: satu baris per indikator, negara, dan tanggal observasi.

Kolom analitik:

| Kolom | Arti |
|---|---|
| `previous_value` / `next_value` | Nilai sebelum dan setelah observasi |
| `rolling_3_period_average` | Rata-rata observasi berjalan, maksimum tiga periode |
| `yoy_absolute_change` | Selisih terhadap tahun sebelumnya jika kedua tahun berurutan |
| `yoy_percent_change` | Persentase perubahan dengan pembagi nol ditangani sebagai `NULL` |

Quality test: `check_mart_indicator_trends_grain.sql`.

## `mart_asean_comparison`

Grain: satu baris per indikator, negara anggota ASEAN saat ini, dan tanggal
observasi.

Mart memakai sebelas anggota ASEAN saat ini: Brunei Darussalam, Kamboja,
Indonesia, Laos, Malaysia, Myanmar, Filipina, Singapura, Thailand, Timor-Leste,
dan Vietnam. Timor-Leste resmi menjadi anggota ke-11 pada 26 Oktober 2025.
Referensi: <https://asean.org/member-states/>.

Data historis seluruh anggota saat ini dipertahankan untuk perbandingan yang
konsisten. `member_since` menyimpan tanggal masuk dan `was_member_during_period`
bernilai 1 hanya jika tanggal observasi berada pada atau setelah tanggal tersebut.

| Kolom | Arti |
|---|---|
| `asean_average` | Rata-rata negara yang memiliki observasi pada indikator/periode |
| `difference_from_asean_average` | Nilai negara dikurangi rata-rata ASEAN |
| `country_coverage` | Jumlah negara dengan observasi yang tersedia |
| `value_rank_desc` | Peringkat nilai terbesar; angka 1 berarti nilai tertinggi |
| `value_percentile` | Posisi 0–1 dari nilai terendah menuju tertinggi |

Peringkat adalah urutan numerik, bukan penilaian baik atau buruk. Nilai inflasi
atau pengangguran yang lebih tinggi tetap mendapat `value_rank_desc` lebih kecil.

Quality test: `check_mart_asean_comparison_grain.sql`.

## Quality queries

Pemeriksaan blocking:

- duplikat natural key pada fakta, staging, dan setiap mart;
- mandatory field kosong;
- nilai di luar rentang logis per indikator;
- run terbaru setiap sumber berstatus gagal.

Laporan informasional:

- waktu ingestion terakhir dan periode observasi terbaru per sumber;
- gap di tengah time series tahunan menggunakan `LEAD`.

Pemeriksaan missing period hanya mendeteksi gap di antara dua observasi yang
tersedia. Ia tidak menganggap periode terbaru yang belum dirilis sebagai error.

`mart_regional_analysis` belum dibuat karena data regional BPS belum tersedia,
sesuai dependensi Fase 2 pada roadmap.
