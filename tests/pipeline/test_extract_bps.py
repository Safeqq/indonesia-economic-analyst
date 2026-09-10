import pytest

import pipelines.extract.extract_bps as bps


def paginated_payload(page: int, pages: int, row_id: int) -> dict:
    return {
        "status": "OK",
        "data-availability": "available",
        "data": [
            {
                "page": page,
                "pages": pages,
                "per_page": 1,
                "count": 1,
                "total": pages,
            },
            [{"th_id": row_id, "th": 2020 + row_id}],
        ],
    }


def test_client_fetches_every_page_and_does_not_return_key(monkeypatch):
    requested_urls: list[str] = []

    def fake_get_json(url, params=None):
        requested_urls.append(url)
        page = 2 if "/page/2/" in url else 1
        return paginated_payload(page, 2, page)

    monkeypatch.setattr(bps, "get_json", fake_get_json)
    client = bps.BPSClient("secret-token")

    requests_made, rows = client.list_paginated(
        "th", domain="0000", filters={"var": 1975}
    )

    assert [row["th_id"] for row in rows] == [1, 2]
    assert len(requests_made) == 2
    assert all("secret-token" in url for url in requested_urls)
    assert all("secret-token" not in item.source_url for item in requests_made)
    assert all("key" not in item.parameters for item in requests_made)


def test_missing_api_key_is_rejected():
    with pytest.raises(RuntimeError, match="BPS_API_KEY"):
        bps.BPSClient("  ")


def test_invalid_pagination_is_rejected(monkeypatch):
    monkeypatch.setattr(
        bps,
        "get_json",
        lambda *args, **kwargs: {
            "status": "OK",
            "data-availability": "available",
            "data": [{"page": 1}, []],
        },
    )

    with pytest.raises(ValueError, match="Metadata pagination"):
        bps.BPSClient("secret").list_paginated("th", domain="0000")


def test_transport_error_does_not_expose_key(monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("bad URL containing secret-token")

    monkeypatch.setattr(bps, "get_json", fail)

    with pytest.raises(RuntimeError) as caught:
        bps.BPSClient("secret-token").request(
            "domain", {"type": "prov"}, context="provinsi"
        )

    assert "secret-token" not in str(caught.value)
