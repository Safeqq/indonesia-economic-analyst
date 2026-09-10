from __future__ import annotations

import os

from pipelines.utils.api_client import get_json

BASE_URL = "https://webapi.bps.go.id/v1/api"


def extract(endpoint: str, params: dict) -> object:
    api_key = os.environ.get("BPS_API_KEY")
    if not api_key:
        raise RuntimeError("BPS_API_KEY belum dikonfigurasi")
    return get_json(f"{BASE_URL}/{endpoint.lstrip('/')}", {**params, "key": api_key})
