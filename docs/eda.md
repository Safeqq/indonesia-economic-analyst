# Exploratory Data Analysis

Fase 5 menyediakan lima notebook yang membaca data nyata dari analytical marts:

| Notebook | Fokus | Sumber utama |
|---|---|---|
| `01_data_profiling.ipynb` | Statistik deskriptif dan missing profile | World Bank, BI, BPS |
| `02_exploratory_analysis.ipynb` | Tren, growth, outlier, seasonality, ASEAN | World Bank, BI |
| `03_correlation_analysis.ipynb` | Matriks dan lagged correlation | World Bank, BI |
| `04_regional_clustering.ipynb` | Segmentasi provinsi jika coverage cukup | BPS |
| `05_time_series_forecasting.ipynb` | Kesiapan time series dan baseline | BI |

Bangun mart, periksa kualitas, lalu jalankan notebook dari root repository:

```fish
make marts
make quality
make eda
```

`make eda` harus dijalankan dengan MariaDB lokal aktif dan konfigurasi database
yang sudah tersedia di `.env`. Runner memakai kernel dari `.venv`, menjalankan
notebook dengan working directory root project, lalu menyimpan:

- notebook ber-output di `data/exports/notebooks/`;
- grafik PNG di `data/exports/eda/`.

Kedua direktori hasil diabaikan Git karena isinya dapat dibuat ulang. Lima file
di `notebooks/` adalah template sumber tanpa execution count dan tanpa output.

## Status data regional

Implementasi clustering sudah tersedia, tetapi hanya berjalan setelah pipeline
BPS produksi mengisi `mart_regional_analysis`. Jika data kosong atau coverage
tidak cukup, notebook menampilkan alasan dan selesai dengan sukses. Perilaku ini
mencegah hasil portofolio dibentuk dari imputasi atau data sintetis.

## Membaca hasil

Setiap insight notebook menyertakan periode, sumber, interpretasi, dan batasan.
Daftar temuan yang telah diverifikasi disimpan di `docs/insights.md`. Korelasi
tidak menyatakan kausalitas, kandidat outlier tidak otomatis merupakan error,
dan baseline historis di notebook kelima bukan forecast masa depan. Perbandingan
ARIMA/SARIMA, quality gate, serta estimasi dengan interval dijelaskan di
`docs/advanced_analytics.md`.
