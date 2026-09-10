import pandas as pd

from analytics.descriptive.data_access import EDADataBundle, dataset_inventory


def test_dataset_inventory_reports_period_source_and_empty_dataset() -> None:
    national = pd.DataFrame(
        {
            "observation_date": pd.to_datetime(["2020-01-01", "2021-01-01"]),
            "value": [1.0, None],
        }
    )
    empty = pd.DataFrame(columns=["observation_date", "value"])
    bundle = EDADataBundle(
        national=national,
        asean=empty.copy(),
        monetary=empty.copy(),
        regional=empty.copy(),
    )

    inventory = dataset_inventory(bundle).set_index("dataset")

    assert inventory.at["national", "row_count"] == 2
    assert inventory.at["national", "period_start"].isoformat() == "2020-01-01"
    assert inventory.at["national", "missing_cells"] == 1
    assert inventory.at["regional", "period_start"] is None
    assert "Badan Pusat Statistik" in inventory.at["regional", "source"]
