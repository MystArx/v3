# tools/warehouse_tools.py
"""
Tools for querying warehouse information based on location and address details.
"""
import logging
from typing import List
from .core_tools import sql_executor, build_parameterized_in_clause # <-- CORRECTED: Import build_parameterized_in_clause
from .data_validator import data_validator
from .region_map import get_region_for_city # <-- CORRECTED: Import get_region_for_city

logger = logging.getLogger(__name__)

def list_warehouses_by_location(filter_type: str, filter_values: List[str]) -> str:
    """
    Lists warehouses filtered by a specific city or region.
    """
    filter_type = filter_type.upper()
    normalized_values = [v.upper().strip() for v in filter_values]
    
    logger.info(f"Listing warehouses for {filter_type} in {normalized_values}")

    if filter_type not in ['CITY', 'REGION']:
        return "ERROR: Invalid filter_type. Must be 'CITY' or 'REGION'."

    all_warehouses = data_validator.get_valid_warehouses()
    matched_codes = set()

    for code in all_warehouses:
        city = data_validator.get_city_for_warehouse(code)
        if not city:
            continue

        for value in normalized_values:
            if filter_type == 'CITY' and city == value:
                matched_codes.add(code)
            elif filter_type == 'REGION' and get_region_for_city(city) == value: # <-- CORRECTED: Use imported function
                matched_codes.add(code)
    
    if not matched_codes:
        return f"INFO: No warehouses found for {filter_type} in {', '.join(normalized_values)}."

    # --- CORRECTED: Use parameterized query to prevent SQL injection ---
    placeholders, values = build_parameterized_in_clause(list(matched_codes))
    query = f"""
        SELECT warehouse_code, warehouse_name, address_1, pin_code
        FROM warehouse_info
        WHERE warehouse_code IN {placeholders}
        ORDER BY warehouse_code;
    """
    
    results = sql_executor(query, "WAREHOUSE", values)
    return f"Found {len(matched_codes)} warehouses for {filter_type} in {', '.join(normalized_values)}:\n{results}"

def find_warehouse_by_address(address_keyword: str) -> str:
    """
    Searches for warehouses using a keyword in their address fields.
    """
    logger.info(f"Searching for warehouses with address keyword: '{address_keyword}'")
    
    search_term = f"%{address_keyword}%"
    query = """
        SELECT warehouse_code, warehouse_name, address_1, address_2, landmark, pin_code
        FROM warehouse_info
        WHERE address_1 LIKE ? OR address_2 LIKE ? OR landmark LIKE ?
        ORDER BY warehouse_code;
    """
    
    results = sql_executor(query, "WAREHOUSE", (search_term, search_term, search_term))
    return f"Search results for address keyword '{address_keyword}':\n{results}"

def get_warehouse_details(warehouse_identifier: str) -> str:
    """
    Returns the address and pincode for a specific warehouse code or name.
    """
    logger.info(f"Fetching details for warehouse: '{warehouse_identifier}'")
    
    # Check if identifier is a valid code first
    is_code = data_validator.validate_warehouse(warehouse_identifier)
    
    if is_code:
        where_clause = "warehouse_code = ?"
        params = (warehouse_identifier,)
    else:
        # --- CORRECTED: Use a flexible LIKE search for names ---
        where_clause = "warehouse_name LIKE ?"
        params = (f"%{warehouse_identifier}%",)

    query = f"""
        SELECT warehouse_code, warehouse_name, address_1, address_2, pin_code, google_map_link
        FROM warehouse_info
        WHERE {where_clause};
    """
    
    results = sql_executor(query, "WAREHOUSE", params)
    return f"Details for warehouse '{warehouse_identifier}':\n{results}"