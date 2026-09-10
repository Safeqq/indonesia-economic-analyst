from pathlib import Path

import nbformat

from scripts.run_eda_notebooks import NOTEBOOK_FILES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_DIRECTORY = PROJECT_ROOT / "notebooks"


def test_phase_five_notebook_set_is_complete() -> None:
    assert NOTEBOOK_FILES == (
        "01_data_profiling.ipynb",
        "02_exploratory_analysis.ipynb",
        "03_correlation_analysis.ipynb",
        "04_regional_clustering.ipynb",
        "05_time_series_forecasting.ipynb",
    )
    assert {path.name for path in NOTEBOOK_DIRECTORY.glob("*.ipynb")} == set(
        NOTEBOOK_FILES
    )


def test_source_notebooks_are_valid_reproducible_templates() -> None:
    required_sections = (
        "## Pertanyaan",
        "## Metode",
        "## Hasil",
        "## Interpretasi",
        "## Keterbatasan",
    )
    for filename in NOTEBOOK_FILES:
        notebook = nbformat.read(NOTEBOOK_DIRECTORY / filename, as_version=4)
        nbformat.validate(notebook)
        markdown = "\n".join(
            str(cell.source) for cell in notebook.cells if cell.cell_type == "markdown"
        )
        for section in required_sections:
            assert section in markdown, f"{filename} tidak memiliki {section}"
        for cell in notebook.cells:
            if cell.cell_type == "code":
                assert cell.execution_count is None
                assert cell.outputs == []


def test_correlation_notebook_rejects_causal_interpretation() -> None:
    notebook = nbformat.read(
        NOTEBOOK_DIRECTORY / "03_correlation_analysis.ipynb", as_version=4
    )
    source = "\n".join(str(cell.source) for cell in notebook.cells).lower()

    assert "korelasi tidak menunjukkan kausalitas" in source
