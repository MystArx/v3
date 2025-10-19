# tools/data_validator.py
"""
Provides data validation and fetching of valid filter values from the database.
This module grounds the LLM by giving it access to the actual data it can query.
"""
import logging
from typing import List, Dict, Set
from .core_tools import sql_executor, extract_city_from_warehouse_code
from .region_map import get_all_regions

logger = logging.getLogger(__name__)

class DataValidator:
    """
    A class to fetch, cache, and provide valid geographical filter values.
    """
    def __init__(self):
        self._valid_regions: Set[str] = set()
        self._valid_cities: Set[str] = set()
        self._valid_warehouses: Set[str] = set()
        self._is_initialized: bool = False

    def initialize(self):
        """
        Fetches all valid values from the database and region map.
        This should be called once at application startup.
        """
        if self._is_initialized:
            return

        logger.info("Initializing DataValidator: fetching valid filter values...")
        
        # 1. Get regions from the region map
        self._valid_regions = get_all_regions()
        logger.info(f"Loaded {len(self._valid_regions)} unique regions.")

        # 2. Get cities and warehouses from the database
        warehouse_query = "SELECT warehouse_code FROM warehouse_info;"
        raw_data = sql_executor(warehouse_query, db_target="WAREHOUSE")

        if raw_data.startswith("ERROR"):
            logger.error("Failed to fetch warehouse data for validator.")
            return

        lines = raw_data.split('\n')
        for line in lines[2:]: # Skip headers
            line = line.strip()
            if not line:
                continue
            
            # Extract warehouse code (assumes simple tuple string format)
            warehouse_code = line.strip("()',\" ")
            if warehouse_code:
                self._valid_warehouses.add(warehouse_code.upper())
                city = extract_city_from_warehouse_code(warehouse_code)
                if city:
                    self._valid_cities.add(city.upper())

        logger.info(f"Loaded {len(self._valid_cities)} unique cities.")
        logger.info(f"Loaded {len(self._valid_warehouses)} unique warehouse codes.")
        self._is_initialized = True
        logger.info("DataValidator initialized successfully.")

    def get_valid_regions(self) -> List[str]:
        return sorted(list(self._valid_regions))

    def get_valid_cities(self) -> List[str]:
        return sorted(list(self._valid_cities))

    def get_valid_warehouses(self) -> List[str]:
        return sorted(list(self._valid_warehouses))

# Singleton instance to be used across the application
data_validator = DataValidator()
