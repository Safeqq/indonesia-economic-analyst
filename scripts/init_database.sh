#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if [[ ! -f .env ]]; then
  echo ".env tidak ditemukan. Jalankan ./scripts/setup_project.sh terlebih dahulu."
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

: "${MYSQL_DATABASE:?MYSQL_DATABASE wajib diisi}"
: "${MYSQL_USER:?MYSQL_USER wajib diisi}"
: "${MYSQL_PASSWORD:?MYSQL_PASSWORD wajib diisi}"

if [[ "$MYSQL_PASSWORD" == "change_me" ]]; then
  echo "Ganti MYSQL_PASSWORD=change_me di .env sebelum melanjutkan."
  exit 1
fi

if [[ ! "$MYSQL_DATABASE" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "MYSQL_DATABASE hanya boleh berisi huruf, angka, dan underscore."
  exit 1
fi

if [[ ! "$MYSQL_USER" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "MYSQL_USER hanya boleh berisi huruf, angka, dan underscore."
  exit 1
fi

escaped_password=${MYSQL_PASSWORD//\'/\'\'}

sudo mariadb <<SQL
CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}\`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'localhost'
  IDENTIFIED BY '${escaped_password}';
ALTER USER '${MYSQL_USER}'@'localhost'
  IDENTIFIED BY '${escaped_password}';
GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

for schema_file in database/schema/02_create_dimensions.sql \
                   database/schema/03_create_facts.sql \
                   database/schema/05_create_metadata_history.sql \
                   database/schema/04_create_indexes.sql; do
  sudo mariadb "$MYSQL_DATABASE" < "$schema_file"
done

echo "Database ${MYSQL_DATABASE} dan tabel awal berhasil disiapkan."
