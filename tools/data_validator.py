# tools/data_validator.py
"""
IMPROVED data validator with fuzzy matching and better error handling.
V2 fixes: Case handling, partial matches, validation reporting
"""
import logging
from typing import List, Dict, Set, Optional
from difflib import get_close_matches
from .core_tools import sql_executor, extract_city_from_warehouse_code
from .region_map import get_all_regions, get_region_for_city

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Enhanced validator with fuzzy matching and comprehensive validation.
    """
    def __init__(self):
        self._valid_regions: Set[str] = set()
        self._valid_cities: Set[str] = set()
        self._valid_warehouses: Set[str] = set()
        self._warehouse_to_city: Dict[str, str] = {}  # Maps warehouse code to city
        self._is_initialized: bool = False

    def initialize(self):
        """
        Fetches all valid values from the database and region map.
        Enhanced with relationship mapping.
        """
        if self._is_initialized:
            logger.info("DataValidator already initialized, skipping...")
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
            raise RuntimeError("Cannot initialize DataValidator: database query failed")

        # Parse warehouse data
        lines = raw_data.split('\n')
        for line in lines[2:]:  # Skip headers
            line = line.strip()
            if not line or line == "()":
                continue
            
            # Extract warehouse code from tuple format
            warehouse_code = line.strip("()',\" ")
            if not warehouse_code:
                continue
            
            # Normalize to uppercase
            warehouse_code = warehouse_code.upper()
            self._valid_warehouses.add(warehouse_code)
            
            # Extract and map city
            city = extract_city_from_warehouse_code(warehouse_code)
            if city:
                self._valid_cities.add(city.upper())
                self._warehouse_to_city[warehouse_code] = city.upper()

        logger.info(f"Loaded {len(self._valid_cities)} unique cities.")
        logger.info(f"Loaded {len(self._valid_warehouses)} unique warehouse codes.")
        
        # Validate region mappings
        self._validate_region_mappings()
        
        self._is_initialized = True
        logger.info("DataValidator initialized successfully.")

    def _validate_region_mappings(self):
        """
        Validates that all cities in database have region mappings.
        Logs warnings for unmapped cities.
        """
        unmapped_cities = []
        for city in self._valid_cities:
            region = get_region_for_city(city)
            if region == "REGION_UNKNOWN":
                unmapped_cities.append(city)
        
        if unmapped_cities:
            logger.warning(f"Found {len(unmapped_cities)} cities without region mappings:")
            for city in unmapped_cities[:10]:  # Show first 10
                logger.warning(f"  - {city}")
            logger.warning("Consider adding these cities to region_map.json")

    def get_valid_regions(self) -> List[str]:
        """Returns sorted list of valid regions."""
        return sorted(list(self._valid_regions))

    def get_valid_cities(self) -> List[str]:
        """Returns sorted list of valid cities."""
        return sorted(list(self._valid_cities))

    def get_valid_warehouses(self) -> List[str]:
        """Returns sorted list of valid warehouse codes."""
        return sorted(list(self._valid_warehouses))

    def fuzzy_match_city(self, city_input: str, threshold: float = 0.7) -> List[str]:
        """
        Finds cities similar to the input using fuzzy matching.
        
        Args:
            city_input: User's input city name
            threshold: Similarity threshold (0-1)
        
        Returns:
            List of matching city names
        """
        normalized_input = city_input.upper().strip()
        matches = get_close_matches(
            normalized_input, 
            list(self._valid_cities), 
            n=5, 
            cutoff=threshold
        )
        return matches

    def fuzzy_match_warehouse(self, warehouse_input: str, threshold: float = 0.8) -> List[str]:
        """
        Finds warehouse codes similar to the input.
        
        Args:
            warehouse_input: User's input warehouse code
            threshold: Similarity threshold (0-1)
        
        Returns:
            List of matching warehouse codes
        """
        normalized_input = warehouse_input.upper().strip()
        matches = get_close_matches(
            normalized_input, 
            list(self._valid_warehouses), 
            n=5, 
            cutoff=threshold
        )
        return matches

    def validate_region(self, region: str) -> bool:
        """Checks if region is valid."""
        return region.upper().strip() in self._valid_regions

    def validate_city(self, city: str) -> bool:
        """Checks if city is valid."""
        return city.upper().strip() in self._valid_cities

    def validate_warehouse(self, warehouse: str) -> bool:
        """Checks if warehouse code is valid."""
        return warehouse.upper().strip() in self._valid_warehouses

    def get_city_for_warehouse(self, warehouse_code: str) -> Optional[str]:
        """
        Returns the city associated with a warehouse code.
        
        Args:
            warehouse_code: Warehouse code
        
        Returns:
            City name or None if not found
        """
        return self._warehouse_to_city.get(warehouse_code.upper().strip())

    def get_warehouses_in_city(self, city: str) -> List[str]:
        """
        Returns all warehouse codes in a given city.
        
        Args:
            city: City name
        
        Returns:
            List of warehouse codes in that city
        """
        normalized_city = city.upper().strip()
        return [
            wh for wh, wh_city in self._warehouse_to_city.items() 
            if wh_city == normalized_city
        ]

    def get_report(self) -> str:
        """
        Generates a validation report for debugging.
        
        Returns:
            Formatted report string
        """
        report = [
            "\n" + "="*70,
            "  DATA VALIDATOR REPORT",
            "="*70,
            f"Regions: {len(self._valid_regions)}",
            f"Cities: {len(self._valid_cities)}",
            f"Warehouses: {len(self._valid_warehouses)}",
            "\nSample Regions:",
        ]
        
        for region in sorted(self._valid_regions):
            report.append(f"  - {region}")
        
        report.append("\nSample Cities (first 10):")
        for city in sorted(self._valid_cities)[:10]:
            report.append(f"  - {city}")
        
        report.append("\nSample Warehouses (first 10):")
        for warehouse in sorted(self._valid_warehouses)[:10]:
            city = self._warehouse_to_city.get(warehouse, "Unknown")
            report.append(f"  - {warehouse} ({city})")
        
        report.append("="*70 + "\n")
        
        return "\n".join(report)


# Singleton instance to be used across the application
data_validator = DataValidator()


if __name__ == "__main__":
    # Test the validator
    logging.basicConfig(level=logging.INFO)
    
    print("Testing DataValidator...")
    data_validator.initialize()
    print(data_validator.get_report())
    
    # Test fuzzy matching
    print("\n--- Fuzzy Matching Tests ---")
    test_inputs = ["ggn", "kohlapur", "dasna", "greater noid"]
    
    for test in test_inputs:
        matches = data_validator.fuzzy_match_city(test)
        print(f"\nInput: '{test}'")
        if matches:
            print(f"Matches: {matches}")
        else:
            print("No matches found")
