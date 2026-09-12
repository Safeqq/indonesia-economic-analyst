# Operasi dan Deployment

## Pemeriksaan sebelum deploy

Jalankan seluruh pemeriksaan dari root project:

```fish
make lint
make test
make test-integration
make frontend-check
make frontend-smoke
make quality
make schedule-dry-run
```

`make test-integration` memerlukan MariaDB lokal dan isi produksi World Bank serta
Bank Indonesia yang sudah dipakai fase sebelumnya. BPS tetap dilaporkan kosong
sampai token dan run produksinya tersedia.

## Konfigurasi secret

Salin `.env.example` jika `.env` belum ada. Ganti `MYSQL_PASSWORD` dan
`MARIADB_ROOT_PASSWORD` dengan nilai kuat yang berbeda. Isi `BPS_API_KEY` pada
host deployment; jangan memasukkan `.env` ke Git. `DEPLOYMENT_VERSION` sebaiknya
diisi dengan commit SHA agar asset dashboard dari release berbeda dapat dikenali.

## Migration

Jalankan migration sebelum aplikasi:

```fish
make schema
```

`make schema` mempertahankan bootstrap schema lama lalu menjalankan semua file
baru di `database/migrations/`. Untuk perubahan berikutnya, tambahkan file baru
seperti `002_add_example.sql`. Jangan ubah file yang sudah tercatat karena runner
akan menolak checksum yang berbeda.

Sebelum migration yang mengubah data, buat backup dan uji bahwa backup dapat
direstore. Contoh backup dijalankan dengan kredensial yang dikelola operator:

```fish
mariadb-dump --single-transaction economic_intelligence > backup.sql
```

Repo tidak menjalankan restore atau rollback otomatis agar data produksi tidak
ditimpa tanpa keputusan operator.

## Menjalankan stack produksi

Validasi konfigurasi dan mulai stack:

```fish
make deployment-config
docker compose --env-file .env -f docker-compose.production.yml up -d --build
docker compose --env-file .env -f docker-compose.production.yml ps
make deployment-smoke
```

Image Python memakai proses Uvicorn dalam exec form. Image dashboard memakai
output Next.js `standalone`. MariaDB tidak memublikasikan port ke host. Service
`migration` menyiapkan schema, migration, dan view sebelum API; dashboard menunggu
healthcheck API.

Pasang reverse proxy dengan TLS di depan port dashboard dan API sebelum akses
publik. Dokumentasi resmi yang menjadi acuan container tersedia pada panduan
[FastAPI](https://fastapi.tiangolo.com/deployment/docker/),
[Next.js](https://nextjs.org/docs/app/getting-started/deploying), dan
[healthcheck MariaDB](https://mariadb.com/docs/server/server-management/automated-mariadb-deployment-and-administration/docker-and-mariadb/using-healthcheck-sh).

## Automation harian

Periksa keputusan scheduler tanpa request ke sumber:

```fish
make schedule-dry-run
```

Untuk menjalankan container automation satu kali:

```fish
docker compose --env-file .env -f docker-compose.production.yml run --rm automation
```

Salin dua template di `deploy/systemd/` ke `/etc/systemd/system/`, lalu sesuaikan
`User` dan `WorkingDirectory` pada service. Aktifkan timer:

```fish
sudo systemctl daemon-reload
sudo systemctl enable --now indonesia-economic-pipeline.timer
systemctl list-timers indonesia-economic-pipeline.timer
```

Timer aktif setiap hari pukul 06:15 Asia/Jakarta. Scheduler sendiri menentukan
sumber yang jatuh tempo. Exit code `0` berarti semua pemeriksaan lulus, `1` berarti
pipeline/quality/freshness menemukan masalah, dan `2` berarti scheduler tidak
dapat dijalankan.

Log ditulis sebagai satu JSON object per baris. Field utama mencakup `timestamp`,
`level`, `event`, `source_code`, `run_id`, jumlah baris, dan durasi bila relevan.
Token dan field dengan nama password, secret, authorization, atau API key
disamarkan.

## Pemulihan

Jika deployment baru gagal, lihat service yang tidak sehat dan log JSON:

```fish
docker compose --env-file .env -f docker-compose.production.yml ps
docker compose --env-file .env -f docker-compose.production.yml logs migration api dashboard
```

Kembalikan image aplikasi ke commit sebelumnya tanpa menghapus volume database.
Jika schema baru perlu diperbaiki, tambahkan migration forward-fix. Jangan memakai
`down -v`, `DROP DATABASE`, atau `TRUNCATE` dalam pemulihan rutin karena perintah
tersebut menghapus data.
