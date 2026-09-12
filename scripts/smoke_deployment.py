from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request

PAGE_PATHS = (
    "/",
    "/trends",
    "/regional",
    "/asean",
    "/drivers",
    "/forecasting",
    "/data-quality",
)


def get(url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "IEI-Smoke/1.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, response.read()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Smoke test deployment API dan dashboard"
    )
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--dashboard-url", default="http://127.0.0.1:3000")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        status, payload = get(f"{args.api_url.rstrip('/')}/health")
        health = json.loads(payload)
        if status != 200 or health.get("status") != "healthy":
            raise RuntimeError("Health API tidak menyatakan status healthy")
        for path in PAGE_PATHS:
            status, html = get(f"{args.dashboard_url.rstrip('/')}{path}")
            if status != 200 or b'lang="id"' not in html:
                raise RuntimeError(f"Dashboard route tidak valid: {path}")
            print(f"[OK] Dashboard route: {path}")
    except (OSError, ValueError, RuntimeError, urllib.error.HTTPError) as error:
        print(f"[FAIL] Smoke deployment gagal: {error}")
        return 1
    print("[OK] API dan seluruh route dashboard dapat dijangkau")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
