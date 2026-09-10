from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "IndonesiaEconomicIntelligence/0.1 (data pipeline)"
DEFAULT_TIMEOUT = (5, 30)
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)


def create_retry_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=RETRY_STATUS_CODES,
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_json(
    url: str,
    params: Mapping[str, str | int] | None = None,
    *,
    session: requests.Session | None = None,
) -> Any:
    if session is not None:
        response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return response.json()

    with create_retry_session() as retry_session:
        response = retry_session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return response.json()
