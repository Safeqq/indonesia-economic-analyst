class ResourceNotFoundError(Exception):
    """Resource yang diminta tidak tersedia."""


class DataIntegrityError(Exception):
    """Data tersimpan tidak memenuhi invariant response API."""
