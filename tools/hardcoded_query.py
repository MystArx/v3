
"""
Main business logic for calculating geographical expenses.
Filters warehouses by REGION, CITY, or WAREHOUSE and aggregates invoice totals.
This version is upgraded to handle a list of filter values.
"""
import logging
from typing import List
from .core_tools import (
    sql_executor,
    extract_city_from_warehouse_code,
    validate_warehouse_ids
)
from .region_map import get_region_for_city

logger = logging.getLogger(__name__)


def calculate_geographical_expenses(filter_type: str, filter_values: List[str]) -> str:
    """
    Calculates total expense amount from invoices for warehouses filtered by a list of geographical values.

    Args:
        filter_type: Must be 'REGION', 'CITY', or 'WAREHOUSE'.
        filter_values: A list of names/codes to filter by (e.g., ['NORTH', 'WEST'], ['DELHI']).

    Returns:
        Formatted string with total expenses or an error message.
    """
    # Normalize inputs
    filter_type = filter_type.upper().strip()
    normalized_filter_values = [fv.upper().strip() for fv in filter_values]
    
    logger.info(f"Calculating expenses for {filter_type} matching {normalized_filter_values}")

    # Validate filter type
    if filter_type not in ["REGION", "CITY", "WAREHOUSE"]:
        return "ERROR: Invalid filter_type. Must be 'REGION', 'CITY', or 'WAREHOUSE'."

    # Step 1: Retrieve all warehouse data once
    warehouse_data_query = "SELECT id, warehouse_code FROM warehouse_info;"
    warehouse_raw_data_str = sql_executor(warehouse_data_query, db_target="WAREHOUSE")

    if warehouse_raw_data_str.startswith("ERROR"):
        return f"ERROR: Failed to retrieve warehouse data: {warehouse_raw_data_str}"

    # Step 2: Parse warehouse data into a map
    warehouse_codes_map = {}
    try:
        lines = warehouse_raw_data_str.split('\n')
        for line in lines[2:]:  # Skip header lines
            line = line.strip()
            if not line:
                continue
            
            clean_line = line.strip("()").replace("'", "").replace('"', '')
            parts = [part.strip() for part in clean_line.split(',', 1)]
            if len(parts) == 2:
                warehouse_id, warehouse_code = parts
                warehouse_codes_map[warehouse_id] = warehouse_code
    except Exception as e:
        logger.error(f"Failed to parse warehouse data: {e}")
        return f"ERROR: Failed to parse warehouse data. Details: {e}"

    if not warehouse_codes_map:
        return "ERROR: No warehouse data found in database."
        
    logger.info(f"Retrieved {len(warehouse_codes_map)} warehouses from database")

    # Step 3: Apply filtering logic for the list of values
    # Use a set to avoid duplicate warehouse IDs
    matched_warehouse_ids = set()

    for wh_id, wh_code in warehouse_codes_map.items():
        clean_wh_code = wh_code.upper().strip()
        city_name = extract_city_from_warehouse_code(clean_wh_code)
        
        for filter_value in normalized_filter_values:
            is_match = False
            if filter_type == "WAREHOUSE" and clean_wh_code == filter_value:
                is_match = True
            elif filter_type == "CITY" and city_name == filter_value:
                is_match = True
            elif filter_type == "REGION" and get_region_for_city(city_name) == filter_value:
                is_match = True
            
            if is_match:
                matched_warehouse_ids.add(wh_id)
                # No need to check other filter_values for this warehouse
                break

    # Step 4: Validate results
    if not matched_warehouse_ids:
        logger.warning(f"No warehouses matched filter: {filter_type}='{normalized_filter_values}'")
        return (
            f"INFO: No warehouses found matching {filter_type} for '{', '.join(normalized_filter_values)}'. "
            f"Please verify the filter values are correct."
        )

    filtered_ids_list = list(matched_warehouse_ids)
    logger.info(f"Filtered to {len(filtered_ids_list)} unique warehouses")

    # Security: Validate warehouse IDs before building query
    if not validate_warehouse_ids(filtered_ids_list):
        return "ERROR: Invalid warehouse IDs detected. Query aborted for security."

    # Step 5: Build and execute final invoice query with all matched IDs
    wh_id_list_str = ', '.join(f"'{wid}'" for wid in filtered_ids_list)

    final_query = f"""
        SELECT
            SUM(total_amount) AS Total_Expenses_Including_GST
        FROM
            invoice_info
        WHERE
            warehouse_id IN ({wh_id_list_str});
    """

    final_results = sql_executor(final_query, db_target="INVOICES")

    if final_results.startswith("ERROR"):
        return f"ERROR: Failed to calculate expenses: {final_results}"

    # Format the final output
    return (
        f"Total expenses (including GST) for {filter_type} '{', '.join(normalized_filter_values)}':\n"
        f"Warehouses matched: {len(filtered_ids_list)}\n"
        f"{final_results}"
    )
