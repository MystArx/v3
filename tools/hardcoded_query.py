# tools/hardcoded_query_tool.py
"""
Main business logic for calculating geographical expenses.
Filters warehouses by REGION, CITY, or WAREHOUSE and aggregates invoice totals.
"""
import logging
from typing import List, Tuple, Dict
from .core_tools import (
    sql_executor, 
    extract_city_from_warehouse_code,
    validate_warehouse_ids
)
from .region_map import get_region_for_city

logger = logging.getLogger(__name__)


def calculate_geographical_expenses(filter_type: str, filter_value: str) -> str:
    """
    Calculates total expense amount from invoices for warehouses filtered by geography.
    
    Args:
        filter_type: Must be 'REGION', 'CITY', or 'WAREHOUSE'
        filter_value: The name/code to filter by (e.g., 'NORTH', 'DELHI', 'DELHI-1')
        
    Returns:
        Formatted string with total expenses or error message
        
    Process:
        1. Query warehouse_info table for all warehouses
        2. Filter warehouses based on filter_type and filter_value
        3. Query invoice_info table for filtered warehouse_ids
        4. Return SUM(total_amount)
    """
    # Normalize inputs
    filter_type = filter_type.upper().strip()
    filter_value = filter_value.upper().strip()
    
    logger.info(f"Calculating expenses for {filter_type}='{filter_value}'")
    
    # Validate filter type
    if filter_type not in ["REGION", "CITY", "WAREHOUSE"]:
        return "ERROR: Invalid filter_type. Must be 'REGION', 'CITY', or 'WAREHOUSE'."
    
    # Step 1: Retrieve warehouse data
    warehouse_data_query = "SELECT id, warehouse_code FROM warehouse_info;"
    warehouse_raw_data_str = sql_executor(warehouse_data_query, db_target="WAREHOUSE")
    
    if warehouse_raw_data_str.startswith("ERROR"):
        return f"ERROR: Failed to retrieve warehouse data: {warehouse_raw_data_str}"
    
    # Step 2: Parse warehouse data
    filtered_warehouse_ids = []
    warehouse_codes_map = {}
    
    try:
        # Parse the formatted output from sql_executor
        lines = warehouse_raw_data_str.split('\n')
        
        # Skip header lines (Columns: [...] and Rows:)
        for line in lines[2:]:
            line = line.strip()
            if not line or line == '':
                continue
            
            # Remove parentheses and quotes
            clean_line = line.strip('()').replace("'", "").replace('"', '')
            parts = [part.strip() for part in clean_line.split(',', 1)]
            
            if len(parts) == 2:
                warehouse_id = parts[0]
                warehouse_code = parts[1]
                warehouse_codes_map[warehouse_id] = warehouse_code
                
    except Exception as e:
        logger.error(f"Failed to parse warehouse data: {e}")
        return f"ERROR: Failed to parse warehouse data. Details: {e}"
    
    if not warehouse_codes_map:
        return "ERROR: No warehouse data found in database."
    
    logger.info(f"Retrieved {len(warehouse_codes_map)} warehouses from database")
    
    # Step 3: Apply filtering logic
    for wh_id, wh_code in warehouse_codes_map.items():
        clean_wh_code = wh_code.upper().strip()
        city_name = extract_city_from_warehouse_code(clean_wh_code)
        
        is_match = False
        
        if filter_type == "WAREHOUSE":
            # Exact match on warehouse code
            if clean_wh_code == filter_value:
                is_match = True
                
        elif filter_type == "CITY":
            # Match on extracted city name
            if city_name == filter_value:
                is_match = True
                
        elif filter_type == "REGION":
            # Match on mapped region
            warehouse_region = get_region_for_city(city_name)
            if warehouse_region == filter_value:
                is_match = True
        
        if is_match:
            filtered_warehouse_ids.append(wh_id)
    
    # Step 4: Validate results
    if not filtered_warehouse_ids:
        logger.warning(f"No warehouses matched filter: {filter_type}='{filter_value}'")
        return (
            f"INFO: No warehouses found matching {filter_type} '{filter_value}'. "
            f"Please verify the filter value is correct."
        )
    
    logger.info(f"Filtered to {len(filtered_warehouse_ids)} warehouses")
    
    # Security: Validate warehouse IDs before building query
    if not validate_warehouse_ids(filtered_warehouse_ids):
        return "ERROR: Invalid warehouse IDs detected. Query aborted for security."
    
    # Step 5: Build and execute final invoice query
    # Note: Using string interpolation here is safe because we've validated IDs are numeric
    wh_id_list_str = ', '.join(filtered_warehouse_ids)
    
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
        f"Total expenses (including GST) for {filter_type} '{filter_value}':\n"
        f"Warehouses matched: {len(filtered_warehouse_ids)}\n"
        f"{final_results}"
    )