# Keterbatasan

## Cakupan data

- Pipeline BPS sudah lengkap secara kode dan test fixture, tetapi database lokal
  belum memiliki observasi produksi BPS karena `BPS_API_KEY` belum tersedia.
  Karena itu target tiga sumber produksi dan analisis 38 provinsi belum selesai.
- Tanggal publikasi tahunan berbeda antarindikator. Jadwal World Bank dan BPS
  adalah waktu pemeriksaan konservatif, bukan jaminan semua angka tahun terbaru
  sudah dirilis pada hari itu.
- Freshness memakai ambang statis per sumber. Hari libur, penundaan publikasi
  resmi, dan revisi kalender sumber belum dimodelkan sebagai kalender khusus.

## Interpretasi analisis

- Korelasi dan lagged correlation tidak membuktikan sebab-akibat.
- Kandidat anomali berasal dari aturan rolling MAD dan masih memerlukan peninjauan
  konteks ekonomi serta catatan revisi sumber.
- Forecast JISDOR adalah estimasi model. Quality gate mengurangi risiko publikasi
  model buruk, tetapi tidak menjamin akurasi periode mendatang.
- Clustering regional baru bermakna setelah dua indikator BPS memiliki coverage
  yang cukup pada tahun yang sama.

## Operasional

- Alert freshness tersedia sebagai JSON log, exit code, dan baris MariaDB. Repo
  belum mengirim email, SMS, atau webhook; integrasi kanal alert harus dilakukan
  oleh sistem monitoring tempat deployment berjalan.
- Compose ditujukan untuk satu host. High availability, replica MariaDB, backup
  terjadwal lintas host, autoscaling, dan koordinasi cache multi-instance belum
  disediakan.
- Compose tidak menyediakan TLS, domain, autentikasi pengguna, WAF, atau rate
  limiting. Pasang reverse proxy dan kontrol akses sesuai lingkungan sebelum
  membuka service ke internet.
- Migration DDL MariaDB dapat melakukan implicit commit. Backup dan uji restore
  tetap wajib sebelum perubahan schema yang tidak kompatibel.
- Smoke test Playwright memakai fixture API terisolasi untuk memeriksa rendering
  tujuh halaman. Integration test API terpisah membaca MariaDB nyata; smoke
  deployment memeriksa konektivitas stack yang sedang berjalan.
