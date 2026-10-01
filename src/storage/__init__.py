"""Storage package for Bronze layer object storage."""
from .r2_client import BronzeStorageManager, get_storage_manager

__all__ = ["BronzeStorageManager", "get_storage_manager"]
