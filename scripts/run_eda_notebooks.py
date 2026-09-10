from __future__ import annotations

import os
import sys
from pathlib import Path

import nbformat
from dotenv import load_dotenv
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

NOTEBOOK_DIRECTORY = PROJECT_ROOT / "notebooks"
EXPORT_DIRECTORY = PROJECT_ROOT / "data" / "exports" / "notebooks"
NOTEBOOK_FILES = (
    "01_data_profiling.ipynb",
    "02_exploratory_analysis.ipynb",
    "03_correlation_analysis.ipynb",
    "04_regional_clustering.ipynb",
    "05_time_series_forecasting.ipynb",
)


def execute_notebook(source: Path, destination: Path) -> None:
    notebook = nbformat.read(source, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=300,
        kernel_name="python3",
        resources={"metadata": {"path": str(PROJECT_ROOT)}},
    )
    try:
        client.execute()
    except CellExecutionError as error:
        raise RuntimeError(f"Notebook gagal dieksekusi: {source.name}") from error
    destination.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, destination)


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    executable_directory = str(Path(sys.executable).parent)
    os.environ["PATH"] = os.pathsep.join(
        [executable_directory, os.environ.get("PATH", "")]
    )
    cache_directory = PROJECT_ROOT / "data" / "exports" / ".matplotlib"
    cache_directory.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_directory))
    for filename in NOTEBOOK_FILES:
        source = NOTEBOOK_DIRECTORY / filename
        if not source.is_file():
            raise FileNotFoundError(f"Notebook wajib tidak ditemukan: {source}")
        destination = EXPORT_DIRECTORY / filename
        execute_notebook(source, destination)
        print(f"[OK] Notebook berhasil: {filename}")
    print(f"[OK] Hasil eksekusi tersimpan di: {EXPORT_DIRECTORY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
