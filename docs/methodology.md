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
Baseline ini belum menjadi forecast produksi; perbandingan model, confidence
interval, metadata model, dan threshold publikasi dikerjakan pada Fase 6.

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
