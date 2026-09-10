import pytest

import pipelines.extract.extract_world_bank as world_bank


def source_record(year: str = "2023", value: float = 5.05) -> dict:
    return {
        "indicator": {"id": "NY.GDP.MKTP.KD.ZG", "value": "GDP growth"},
        "country": {"id": "ID", "value": "Indonesia"},
        "countryiso3code": "IDN",
        "date": year,
        "value": value,
    }


def test_valid_api_response_can_be_extracted(monkeypatch):
    payload = [{"page": 1, "total": 1}, [source_record()]]
    captured: dict[str, object] = {}

    def fake_get_json(url, params):
        captured.update(url=url, params=params)
        return payload

    monkeypatch.setattr(world_bank, "get_json", fake_get_json)

    result = world_bank.extract_indicator(
        "IDN", "NY.GDP.MKTP.KD.ZG", 2020, 2023
    )

    assert result.payload is payload
    assert result.records == payload[1]
    assert captured["params"]["date"] == "2020:2023"
    assert captured["url"].endswith("/country/IDN/indicator/NY.GDP.MKTP.KD.ZG")


def test_invalid_year_range_is_rejected(monkeypatch):
    def unexpected_request(*args, **kwargs):
        raise AssertionError("HTTP request tidak boleh dijalankan")

    monkeypatch.setattr(world_bank, "get_json", unexpected_request)

    with pytest.raises(ValueError, match="Tahun awal"):
        world_bank.extract_indicator("IDN", "NY.GDP.MKTP.KD.ZG", 2024, 2023)


@pytest.mark.parametrize("payload", [{}, [], [{"page": 1}], [{}, None]])
def test_invalid_api_response_is_rejected(monkeypatch, payload):
    monkeypatch.setattr(world_bank, "get_json", lambda *args, **kwargs: payload)

    with pytest.raises(ValueError, match="respons tidak valid"):
        world_bank.extract_indicator("IDN", "NY.GDP.MKTP.KD.ZG", 2020, 2023)
