#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 belum terpasang. Instal dengan: sudo pacman -S python"
  exit 1
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js dan npm belum terpasang. Instal dengan: sudo pacman -S nodejs npm"
  exit 1
fi

node - <<'JS'
const [major, minor] = process.versions.node.split(".").map(Number);
if (major < 20 || (major === 20 && minor < 9)) {
  console.error("Dashboard membutuhkan Node.js 20.9 atau lebih baru");
  process.exit(1);
}
console.log(`Node.js ${process.versions.node} terdeteksi`);
JS

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
npm --prefix frontend ci

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo ".env dibuat. Ganti MYSQL_PASSWORD sebelum inisialisasi database."
else
  echo ".env sudah ada; file tidak ditimpa."
fi

mkdir -p data/raw/bps data/raw/bank_indonesia data/raw/world_bank
mkdir -p data/processed data/exports logs

echo "Setup project selesai. Langkah berikutnya: edit .env lalu jalankan ./scripts/init_database.sh"
