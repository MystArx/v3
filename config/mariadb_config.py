# config/mariadb_config.py
"""
Database configuration for Invoice and Warehouse databases.
Centralized connection management with validation.
"""
from typing import Dict, Any
import os

# --- Database Connection Configurations ---

# Configuration for the Database holding Invoice Transactions
MARIADB_CONFIG_INVOICES: Dict[str, Any] = {
    "user": os.getenv("DB_USER", "user"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("INVOICES_DB", "invoices_copy"),
    "autocommit": False,  # Explicit transaction control
}

# Configuration for the Database holding Master Data (Warehouse Info)
MARIADB_CONFIG_WAREHOUSE: Dict[str, Any] = {
    "user": os.getenv("DB_USER", "user"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("WAREHOUSE_DB", "warehouses_copy"),
    "autocommit": False,
}

# Map names to configurations for easy lookup in sql_executor
DB_CONNECTION_MAP: Dict[str, Dict[str, Any]] = {
    "INVOICES": MARIADB_CONFIG_INVOICES,
    "WAREHOUSE": MARIADB_CONFIG_WAREHOUSE
}

def validate_config(config: Dict[str, Any]) -> bool:
    """Validate that all required configuration keys are present."""
    required_keys = {"user", "password", "host", "port", "database"}
    return all(key in config for key in required_keys)

def get_db_config(db_name: str) -> Dict[str, Any]:
    """
    Safely retrieve database configuration with validation.
    
    Args:
        db_name: Either 'INVOICES' or 'WAREHOUSE'
        
    Returns:
        Dictionary containing database configuration
        
    Raises:
        ValueError: If db_name is invalid or config is incomplete
    """
    if db_name not in DB_CONNECTION_MAP:
        raise ValueError(
            f"Invalid database name: {db_name}. "
            f"Must be one of: {list(DB_CONNECTION_MAP.keys())}"
        )
    
    config = DB_CONNECTION_MAP[db_name]
    if not validate_config(config):
        raise ValueError(f"Incomplete configuration for database: {db_name}")
    
    return config.copy()  # Return a copy to prevent modification