from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDICATOR_CONFIG = PROJECT_ROOT / "config" / "indicators.yml"


@dataclass(frozen=True)
class IndicatorDefinition:
    code: str
    name: str
    unit: str
    frequency: str
    source: str


def load_indicator_definitions(
    path: Path = DEFAULT_INDICATOR_CONFIG,
) -> dict[str, IndicatorDefinition]:
    with path.open(encoding="utf-8") as config_file:
        payload = yaml.safe_load(config_file)

    if not isinstance(payload, dict) or not isinstance(payload.get("indicators"), list):
        raise ValueError(f"Konfigurasi indikator tidak valid: {path}")

    definitions: dict[str, IndicatorDefinition] = {}
    required_fields = {"code", "name", "unit", "frequency", "source"}
    for position, item in enumerate(payload["indicators"], start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Indikator ke-{position} harus berupa mapping")
        missing = required_fields.difference(item)
        if missing:
            raise ValueError(
                f"Indikator ke-{position} tidak memiliki field: {sorted(missing)}"
            )
        definition = IndicatorDefinition(
            code=str(item["code"]),
            name=str(item["name"]),
            unit=str(item["unit"]),
            frequency=str(item["frequency"]),
            source=str(item["source"]),
        )
        if definition.code in definitions:
            raise ValueError(f"Kode indikator duplikat: {definition.code}")
        definitions[definition.code] = definition

    return definitions
