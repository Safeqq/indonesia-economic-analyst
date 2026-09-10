"""Connector Bank Indonesia.

Implementasikan parser hanya setelah tabel statistik dan format unduhan yang
dipilih dicatat di docs/data_sources.md. Tidak ada fallback ke data buatan.
"""


def extract() -> list[dict]:
    raise NotImplementedError("Pilih tabel resmi BI sebelum mengaktifkan connector")
