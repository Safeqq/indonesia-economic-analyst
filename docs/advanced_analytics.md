# Advanced Analytics

Fase 6 menjalankan forecasting dan deteksi anomali pada rata-rata JISDOR
bulanan dari `mart_monetary_conditions`. Konfigurasi versi model berada di
`config/advanced_analytics.yml`; tidak ada angka forecast yang ditanam di kode.

## Menjalankan proses

Pastikan pipeline Bank Indonesia dan mart sudah terisi, lalu jalankan:

```fish
make schema
make advanced-analytics
make verify-analytics
make quality
```

`make advanced-analytics` membaca data dari MariaDB, mengevaluasi model,
menjalankan quality gate, menyimpan hasil secara transaksional, dan membuat
artefak JSON serta PNG di `data/exports/advanced_analytics/`. Direktori hasil
diabaikan Git karena semua artefak dapat dibuat ulang dari data dan konfigurasi.

Run memakai fingerprint SHA-256 dari data dan konfigurasi sebagai natural key.
Menjalankan ulang proses dengan input yang sama memperbarui run yang sama serta
mengganti baris anaknya, sehingga tidak menambah forecast atau anomali duplikat.

## Evaluasi forecasting

Target awal adalah `BI.JISDOR.USD_IDR.MONTHLY_AVG` untuk Indonesia. Seri wajib
bulanan, unik, finite, dan tanpa periode hilang. Data tidak diimputasi.

Evaluasi memakai 24 bulan terakhir sebagai holdout berdasarkan waktu. Setiap
model membuat prediksi satu langkah ke depan dan baru menerima nilai aktual
holdout setelah prediksi periode itu selesai. Model yang dibandingkan adalah:

- naïve lag-1;
- seasonal-naïve lag-12;
- ARIMA(0,1,1) dengan drift;
- SARIMA(0,1,1)(0,1,1,12).

MAE menjadi metrik pemilihan utama. RMSE dan MAPE ikut disimpan; observasi dengan
nilai aktual nol tidak dipakai sebagai penyebut MAPE. ARIMA dan SARIMA juga
menyimpan cakupan interval pada holdout, AIC, BIC, status konvergensi, warning,
parameter, setiap prediksi out-of-sample, serta versi library.

Model lanjutan dengan MAE terendah hanya boleh menghasilkan estimasi masa depan
jika seluruh batas berikut terpenuhi:

| Pemeriksaan | Batas |
|---|---:|
| Perbaikan MAE terhadap baseline terbaik | minimal 5% |
| MAPE model terpilih | maksimal 5% |
| Cakupan interval holdout | minimal 70% |
| Konvergensi | wajib berhasil |

Jika satu syarat gagal, run tetap menyimpan evaluasi dan alasan kegagalan, tetapi
tidak membuat baris di `fact_forecast`. Jika lulus, enam bulan estimasi disimpan
bersama interval 95% dan `is_publishable = 1`. Nilai tersebut tetap merupakan
estimasi model, bukan observasi resmi atau kepastian nilai tukar.

## Deteksi anomali

Metode awal memakai perubahan JISDOR antarbulan. Untuk setiap titik, median dan
median absolute deviation (MAD) dihitung dari maksimal 24 perubahan sebelumnya,
dengan minimal 12 observasi historis. Robust score dihitung sebagai
`0.67448975 * (perubahan - median) / MAD`; titik dengan nilai absolut minimal
3,5 disimpan sebagai `economic_anomaly` untuk ditinjau.

Klasifikasi dipisahkan agar maknanya tidak tercampur:

| Klasifikasi | Dasar penetapan |
|---|---|
| `missing_value` | periode kalender atau nilainya tidak tersedia |
| `source_revision` | revisi dikonfirmasi melalui metadata yang diberikan ke detector |
| `economic_anomaly` | perubahan melewati threshold statistik dan bukan revisi terkonfirmasi |

Setiap event menyimpan metode, threshold, nilai/perubahan bila tersedia, score,
dan alasan yang dapat dibaca. Label `economic_anomaly` hanya berarti kandidat
perubahan ekonomi yang tidak biasa. Pipeline tidak menyimpulkan penyebab dan
tidak menganggap titik tersebut sebagai kesalahan data. Revisi sumber juga tidak
ditebak dari besar perubahan; label itu hanya dipakai jika ada konfirmasi sumber.

## Hasil run tervalidasi

Run 10 September 2026 memakai 121 observasi Agustus 2016–Agustus 2026. Holdout
September 2024–Agustus 2026 menghasilkan:

| Model | MAE | RMSE | MAPE | Cakupan interval 95% |
|---|---:|---:|---:|---:|
| naïve lag-1 | 183,49 | 226,08 | 1,11% | n/a |
| seasonal-naïve lag-12 | 681,78 | 831,66 | 4,01% | n/a |
| ARIMA(0,1,1) + drift | 156,14 | 200,81 | 0,94% | 95,83% |
| SARIMA(0,1,1)(0,1,1,12) | 222,26 | 251,97 | 1,34% | 95,83% |

ARIMA memperbaiki MAE 14,91% dibanding baseline terbaik dan lulus quality gate.
Enam estimasi September 2026–Februari 2027 dibuat dengan interval yang makin
lebar seiring horizon. Delapan perubahan historis ditandai sebagai kandidat
anomali ekonomi; setiap alasan numeriknya tersedia pada artefak dan database.

Hasil ini bergantung pada versi data saat run, spesifikasi model yang terbatas,
dan holdout 24 bulan. Kinerja historis tidak menjamin akurasi masa depan.
