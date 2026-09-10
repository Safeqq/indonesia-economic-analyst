# Validated Insights

Insight berikut dihasilkan oleh `make eda` pada 10 September 2026. Angka dapat
berubah setelah sumber merevisi data atau pipeline mengambil periode baru.

- **Kelengkapan nasional.** Mart nasional berisi 26 tahun (2000–2025) dan seluruh
  tahun lengkap untuk GDP growth, inflasi, pengangguran, populasi, serta GDP per
  kapita. Sumber: World Bank Indicators API v2. Kelengkapan tidak menjamin data
  tidak akan direvisi. Reproduksi: `01_data_profiling.ipynb`.
- **Kondisi terbaru dan growth rate.** Pada 2025, GDP Indonesia tumbuh 5,11%,
  inflasi 1,91%, dan pengangguran 3,24%. Dibanding 2024, populasi tumbuh 0,79%
  dan GDP per kapita nominal USD tumbuh 2,72%. Periode: 2024–2025. Sumber: World
  Bank Indicators API v2. GDP per kapita nominal USD juga dipengaruhi perubahan
  harga dan kurs. Reproduksi: `02_exploratory_analysis.ipynb`.
- **Kandidat outlier.** Aturan IQR menandai enam observasi pada data 2000–2025:
  GDP growth 2001, 2020, dan 2021 serta inflasi 2001, 2002, dan 2006. Sumber:
  World Bank Indicators API v2. Label IQR hanya menandai titik untuk ditinjau;
  titik tersebut tidak otomatis salah atau merupakan anomali ekonomi. Reproduksi:
  `02_exploratory_analysis.ipynb`.
- **Perbandingan ASEAN.** Pertumbuhan GDP Indonesia pada 2025 berada di urutan
  nilai ke-5 dari 11 negara anggota ASEAN saat ini yang memiliki observasi.
  Sumber: World Bank Indicators API v2. Peringkat mengurutkan angka dan bukan
  penilaian kualitas ekonomi. Reproduksi: `02_exploratory_analysis.ipynb`.
- **Pola bulan kalender JISDOR.** Maret memiliki rata-rata perubahan bulanan
  JISDOR tertinggi, sebesar 1,80%, ketika observasi Agustus 2016–Agustus 2026
  dikelompokkan berdasarkan bulan kalender. Sumber: Bank Indonesia. Rentang ini
  hanya mencakup sekitar sepuluh tahun dan tahun tepi tidak lengkap, sehingga
  hasil belum membuktikan pola musiman yang stabil. Reproduksi:
  `02_exploratory_analysis.ipynb`.
- **Korelasi.** Korelasi Pearson absolut terbesar pada matriks adalah 0,976 antara
  populasi dan GDP per kapita nominal USD, berdasarkan 26 observasi tahunan
  2000–2025. Pada rentang lag -3 sampai 3, korelasi absolut terbesar antara GDP
  growth dan inflasi adalah 0,310 ketika inflasi digeser dua tahun ke belakang,
  berdasarkan 24 pasangan observasi. Sumber: World Bank Indicators API v2.
  Tren bersama, pemilihan lag, dan variabel lain dapat membentuk korelasi semu;
  korelasi ini tidak menunjukkan kausalitas. Reproduksi:
  `03_correlation_analysis.ipynb`.
- **Baseline JISDOR.** Seri Bank Indonesia memiliki 121 bulan tanpa gap di antara
  Agustus 2016 dan Agustus 2026. Pada holdout September 2024–Agustus 2026,
  baseline naïve lag-1 menghasilkan MAE 183,49 IDR/USD, RMSE 226,08, dan MAPE
  1,11%; seasonal-naïve lag-12 memiliki MAE 681,78, RMSE 831,66, dan MAPE 4,01%.
  Ini backtest rolling historis, belum forecast masa depan dan belum memiliki
  confidence interval. Reproduksi: `05_time_series_forecasting.ipynb`.
- **Segmentasi regional.** Belum ada hasil clustering karena mart BPS belum berisi
  observasi produksi. Periode: belum tersedia. Sumber yang ditunggu: BPS Web API.
  Notebook menghentikan analisis tanpa imputasi atau data sintetis. Reproduksi:
  `04_regional_clustering.ipynb`.
