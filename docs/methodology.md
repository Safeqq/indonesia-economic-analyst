# Methodology

## Exploratory data analysis

Seluruh notebook membaca analytical mart MariaDB melalui fungsi yang sama di
`analytics/descriptive/data_access.py`. Notebook sumber tidak menyimpan hasil
eksekusi. `make eda` menjalankannya berurutan dan menulis salinan ber-output ke
`data/exports/notebooks/`, sehingga tabel dan grafik dapat direproduksi dari isi
database saat itu.

Missing value dilaporkan apa adanya dan tidak diimputasi. Growth rate memakai
perubahan persentase dari observasi sebelumnya dengan pembagi nol menjadi nilai
kosong. Kandidat outlier memakai batas IQR 1,5 kali rentang antarkuartil; label
ini adalah petunjuk pemeriksaan, bukan bukti kesalahan data atau kejadian ekonomi.

Eksplorasi seasonality mengelompokkan seri bulanan menurut bulan kalender dan
membandingkan mean, median, minimum, serta maksimum. Pola tersebut belum dianggap
seasonality yang stabil sebelum diuji pada periode yang memadai.

Korelasi Pearson dihitung secara pairwise dan selalu disertai jumlah observasi
yang overlap. Lag positif membandingkan target pada periode sekarang dengan
fitur pada periode sebelumnya. Korelasi, termasuk lagged correlation, tidak
diperlakukan sebagai bukti kausalitas.

Clustering regional hanya berjalan jika satu tahun memiliki sedikitnya dua
indikator BPS yang lengkap pada minimal empat provinsi. Fitur distandardisasi,
jumlah cluster dipilih berdasarkan silhouette score, dan PCA hanya dipakai untuk
visualisasi. Proses tidak mengisi missing value dan tidak membuat fallback data
sintetis.

Notebook time series memakai holdout berdasarkan waktu. Naïve lag-1 dan
seasonal-naïve lag-12 dievaluasi dengan MAE, RMSE, serta MAPE yang mengabaikan
nilai aktual nol hanya pada penyebut MAPE. Evaluasi bersifat rolling one-step:
nilai aktual sebelumnya di dalam holdout dapat menjadi input prediksi berikutnya.
Baseline notebook menjadi pembanding yang sama untuk advanced analytics.

## Forecasting dan quality gate

Advanced analytics memakai 24 observasi terakhir sebagai holdout kronologis.
Naïve lag-1 dan seasonal-naïve lag-12 dibandingkan dengan ARIMA(0,1,1) dengan drift
dan SARIMA(0,1,1)(0,1,1,12). Parameter model dipasang hanya pada bagian training;
setiap prediksi holdout dibuat sebelum observasi aktual periode itu ditambahkan
ke state model tanpa refit. Model final baru dipasang pada seluruh seri setelah
evaluasi selesai.

Model lanjutan dipilih berdasarkan MAE terendah. Forecast masa depan hanya dibuat
jika model konvergen, memperbaiki MAE minimal 5% dari baseline terbaik, memiliki
MAPE maksimal 5%, dan interval 95% mencakup minimal 70% observasi holdout. Jika
gate gagal, alasan dan hasil evaluasi tetap disimpan tetapi tabel forecast tidak
diisi untuk run tersebut. Forecast yang lulus selalu diberi interval dan label
estimasi, bukan fakta observasi.

## Deteksi anomali

Deteksi awal memakai robust score dari perubahan antarbulan terhadap median dan
MAD pada maksimal 24 perubahan sebelumnya. Minimal 12 perubahan historis wajib
tersedia dan threshold absolutnya 3,5. Missing value dicatat terpisah berdasarkan
kalender. Revisi sumber hanya dilabeli jika ada konfirmasi eksplisit yang diberikan
ke detector. Titik lain yang melewati threshold disebut kandidat anomali ekonomi,
bukan bukti kesalahan data atau penjelasan sebab-akibat. Formula, alasan numerik,
dan klasifikasi disimpan untuk setiap event.

## Normalisasi data Bank Indonesia

BI-Rate pada tanggal keputusan dibawa ke posisi akhir setiap bulan: nilai yang
dipilih adalah keputusan terakhir pada atau sebelum hari terakhir bulan tersebut.
JISDOR bulanan adalah rata-rata aritmetika seluruh observasi harian resmi yang
tersedia dalam bulan. Hari tanpa publikasi tidak diimputasi. Bulan berjalan yang
belum selesai tidak dimuat agar rata-rata parsial tidak dibandingkan dengan bulan
lengkap.

Kedua hasil memakai tanggal pertama bulan sebagai label periode dan tetap diberi
nama yang menjelaskan transformasinya. Snapshot sumber mentah dipertahankan agar
angka turunan dapat dihitung ulang dan direkonsiliasi.

## Jadwal, retry, dan freshness

Frekuensi publikasi model menentukan cadence scheduler. Seri bulanan Bank
Indonesia diperiksa sesudah hari kelima bulan berikutnya agar bulan kalender
sebelumnya sudah lengkap. Seri tahunan World Bank dan BPS diperiksa sekali per
tahun setelah tanggal konfigurasi. Scheduler harian hanya bertugas mengevaluasi
keputusan tersebut; `--force` disediakan untuk backfill atau pemulihan manual.
Cadence membaca run sukses dari `pipeline_schedule_run`, sehingga run manual yang
mungkin hanya mencakup sebagian negara atau indikator tidak menutup jadwal sumber.

HTTP GET sudah memiliki retry pada tingkat request. Scheduler menambahkan retry
terbatas pada tingkat job untuk timeout, kegagalan koneksi, HTTP 429, HTTP 5xx,
dan `OperationalError` database. Delay bertambah secara eksponensial. Error
konfigurasi, schema drift, parsing, atau validasi tidak dicoba ulang. Setiap
attempt tetap tercatat, sedangkan fakta memakai upsert transaksional pada natural
key sehingga pengulangan tidak menggandakan observasi.

Freshness dinilai dari dua sinyal: umur `ingested_at` terbaru dan jarak tanggal
observasi terbaru terhadap waktu pemeriksaan. Ambang berbeda per sumber dan
disimpan di `config/automation.yml`. Tidak adanya run sukses atau observasi adalah
alert kritis. Pelampauan ambang waktu adalah warning yang tetap menghasilkan exit
code gagal agar systemd, CI, atau monitor eksternal dapat menangkapnya.

## Strategi migration

Migration bersifat forward-only dan berurutan. Nama file memakai format
`NNN_nama_deskriptif.sql`. SHA-256 setiap file disimpan di `schema_migration`;
checksum yang berubah menghentikan proses agar riwayat database tidak ditulis
ulang diam-diam. Perubahan harus backward-compatible selama API lama masih hidup.
Sebelum migration yang mengubah data atau kolom, buat backup MariaDB dan uji
restore. Rollback dilakukan dengan mengembalikan image aplikasi lalu menerapkan
forward-fix; file migration lama tidak diedit.

Semua koneksi aplikasi menetapkan session MariaDB ke UTC. Timestamp operasional
disimpan dan dibandingkan sebagai UTC agar umur ingestion tidak bergantung pada
timezone host database; tanggal observasi ekonomi tetap memakai tanggal sumber.
