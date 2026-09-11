from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.utils.data_quality import run_quality_checks  # noqa: E402


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    failed = False
    for result in run_quality_checks():
        if result.blocking and result.rows:
            failed = True
            label = "FAIL"
        elif result.blocking:
            label = "OK"
        else:
            label = "INFO"
        print(f"[{label}] {result.name}: {len(result.rows)} baris")
        if result.rows:
            for row in result.rows[:3]:
                print(f"  {row}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
