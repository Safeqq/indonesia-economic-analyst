# Dashboard Next.js

Dashboard Fase 8 menyajikan data dari FastAPI secara read-only. Nilai observasi,
periode, satuan, sumber, waktu ingestion, hasil quality check, dan forecast selalu
berasal dari API; source code frontend tidak memuat angka produksi sebagai
fallback.

## Menjalankan dashboard

Pastikan dependensi sudah terpasang melalui `./scripts/setup_project.sh` atau
`make frontend-install`. Gunakan dua terminal:

```fish
# Terminal 1
make api

# Terminal 2
make dashboard
```

Buka `http://localhost:3000`. Next.js meneruskan `/backend/*` ke
`http://127.0.0.1:8000` agar browser memakai origin yang sama. Alamat tujuan dapat
diganti pada proses Next.js tanpa mengekspos kredensial:

```fish
env API_BASE_URL=https://api.example.id make dashboard
```

## Halaman

| Halaman | Isi utama |
|---|---|
| Executive Overview | KPI nasional/moneter terbaru dan tren indikator terpilih |
| Trend Explorer | Time series, perubahan, rentang nilai, tabel observasi |
| Regional Analysis | Perbandingan provinsi pada indikator dan tahun yang sama |
| ASEAN Benchmark | Nilai, rata-rata kawasan, selisih, peringkat, dan persentil |
| Correlation & Drivers | Scatter plot dan heatmap Pearson pada tanggal beririsan |
| Forecasting Lab | Aktual, estimasi, interval, metrik holdout, dan quality gate |
| Data Quality Center | Blocking checks, temuan informasi, dan riwayat pipeline |

Filter indikator, wilayah, negara, serta awal/akhir periode berada pada shell
global dan tetap aktif saat berpindah halaman. Daftar filter datang dari endpoint
katalog. Saat indikator diganti, periode kembali ke sepuluh tahun terakhir yang
benar-benar tersedia untuk seri tersebut.

Setiap halaman menangani loading, hasil kosong, dan error API secara eksplisit.
Tombol **Export CSV** hanya mengekspor baris sesuai filter aktif serta menyertakan
metadata yang relevan. Grafik memiliki tooltip periode dan nilai yang diformat
dengan satuan indikator.

Regional Analysis memakai comparison chart. Choropleth sengaja belum diaktifkan
karena repository belum memiliki pasangan geometri batas provinsi dan kode BPS
yang telah divalidasi. Hal ini mencegah nilai dipetakan ke wilayah yang salah.

Forecasting Lab hanya menampilkan titik dari run yang lolos quality gate dan
menandainya sebagai estimasi model. Jika indikator aktif belum memiliki forecast,
halaman menampilkan empty state serta pintasan ke seri JISDOR yang sudah memiliki
run tervalidasi bila tersedia di katalog.

## Verifikasi frontend

```fish
make frontend-lint
make frontend-test
make frontend-build

# Menjalankan semuanya berurutan
make frontend-check
```

`make lint` dan `make test` juga mencakup pemeriksaan frontend, sehingga regresi
Python dan TypeScript diperiksa melalui perintah utama project.
