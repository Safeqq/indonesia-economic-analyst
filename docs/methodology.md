# Methodology

Gunakan time-based split untuk forecasting, tampilkan baseline, dan dokumentasikan
keterbatasan. Korelasi tidak diperlakukan sebagai bukti kausalitas.

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
