#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 belum terpasang. Instal dengan: sudo pacman -S python"
  exit 1
fi

python3 - <<'PY'
import sys

if sys.version_info < (3, 11):
    raise SystemExit("Project membutuhkan Python 3.11 atau lebih baru")
print(f"Python {sys.version.split()[0]} terdeteksi")
PY

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo ".env dibuat. Ganti MYSQL_PASSWORD sebelum inisialisasi database."
else
  echo ".env sudah ada; file tidak ditimpa."
fi

mkdir -p data/raw/bps data/raw/bank_indonesia data/raw/world_bank
mkdir -p data/processed data/exports logs

echo "Setup Python selesai. Langkah berikutnya: edit .env lalu jalankan ./scripts/init_database.sh"
