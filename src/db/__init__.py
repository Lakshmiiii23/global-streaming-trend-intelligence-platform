"""Database management package for Silver and Gold layers."""
from .postgres_client import DatabaseManager, get_db_manager

__all__ = ["DatabaseManager", "get_db_manager"]
