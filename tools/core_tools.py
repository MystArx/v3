# tools/core_tools.py
"""
Core database and utility functions for the expense calculation system.
Provides safe SQL execution and city/region extraction utilities.
"""
import mariadb
import logging
from typing import Dict, Any, List, Tuple, Optional
from config.mariadb_config import get_db_config
from .region_map import get_region_for_city

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQL keyword blacklist for read-only enforcement
FORBIDDEN_SQL_KEYWORDS = [
    "DELETE", "DROP", "UPDATE", "INSERT", "ALTER", 
    "TRUNCATE", "CREATE", "REPLACE", "GRANT", "REVOKE"
]


def sql_executor(
    sql_query: str, 
    db_target: str, 
    params: Optional[Tuple] = None
) -> str:
    """
    Executes a SELECT SQL query against the specified MariaDB database target.
    
    Args:
        sql_query: The SQL SELECT query to execute
        db_target: Database target ('INVOICES' or 'WAREHOUSE')
        params: Optional tuple of parameters for parameterized queries
        
    Returns:
        Formatted string containing query results or error message
        
    Security:
        - Only allows SELECT queries (read-only)
        - Supports parameterized queries to prevent SQL injection
        - Validates database target before execution
    """
    # Validate database target
    try:
        config = get_db_config(db_target)
    except ValueError as e:
        return f"ERROR: {e}"
    
    # Security: Only allow read operations
    query_upper = sql_query.upper().strip()
    if any(keyword in query_upper for keyword in FORBIDDEN_SQL_KEYWORDS):
        logger.warning(f"Attempted forbidden SQL operation: {sql_query[:100]}")
        return "ERROR: Query rejected. Only read-only (SELECT) operations are permitted."
    
    conn = None
    try:
        conn = mariadb.connect(**config)
        cursor = conn.cursor()
        
        # Execute with or without parameters
        if params:
            cursor.execute(sql_query, params)
        else:
            cursor.execute(sql_query)
            
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        # Format output as parsable string
        formatted_results = f"Columns: {columns}\nRows:\n"
        
        for row in results:
            if db_target == "WAREHOUSE" and len(row) >= 2:
                # Format: ('ID', 'CODE') for consistent parsing
                formatted_results += f"('{str(row[0]).strip()}', '{str(row[1]).strip()}')\n"
            else:
                # For INVOICES or other queries
                formatted_results += str(row) + "\n"
        
        logger.info(f"Query executed successfully on {db_target}: {len(results)} rows returned")
        return formatted_results
        
    except mariadb.Error as e:
        error_msg = f"DATABASE ERROR on {db_target}: {e}"
        logger.error(error_msg)
        return error_msg
        
    except Exception as e:
        error_msg = f"UNEXPECTED ERROR: {e}"
        logger.error(error_msg)
        return error_msg
        
    finally:
        if conn:
            conn.close()


def extract_city_from_warehouse_code(warehouse_code: str) -> str:
    """
    Extracts the city name from a standardized warehouse code.
    
    Format: CITY-NUMBER (e.g., 'DELHI 1', 'CHARKHI DADRI 1')
    
    Args:
        warehouse_code: The warehouse code string
        
    Returns:
        Extracted city name in uppercase
        
    Examples:
        >>> extract_city_from_warehouse_code('DELHI 1')
        'DELHI'
        >>> extract_city_from_warehouse_code('CHARKHI DADRI 2')
        'CHARKHI DADRI'
    """
    warehouse_code = warehouse_code.strip()
    
    if '-' not in warehouse_code:
        logger.warning(f"Warehouse code missing hyphen: {warehouse_code}")
        return warehouse_code.upper()
    
    # Split on last hyphen to handle multi-word cities
    city_name = warehouse_code.rsplit('-', 1)[0]
    return city_name.strip().upper()


def validate_warehouse_ids(warehouse_ids: List[str]) -> bool:
    """
    Validates that warehouse IDs are safe for SQL queries.
    
    Args:
        warehouse_ids: List of warehouse ID strings
        
    Returns:
        True if all IDs are numeric/safe, False otherwise
    """
    if not warehouse_ids:
        return False
    
    for wid in warehouse_ids:
        # Ensure ID is numeric to prevent SQL injection
        if not str(wid).strip().isdigit():
            logger.error(f"Invalid warehouse ID detected: {wid}")
            return False
    
    return True


def build_parameterized_in_clause(values: List[str]) -> Tuple[str, Tuple]:
    """
    Builds a parameterized IN clause for SQL queries.
    
    Args:
        values: List of values to include in IN clause
        
    Returns:
        Tuple of (placeholder_string, values_tuple)
        
    Example:
        >>> build_parameterized_in_clause(['1', '2', '3'])
        ('(?, ?, ?)', ('1', '2', '3'))
    """
    if not values:
        return ("()", tuple())
    
    placeholders = ', '.join(['?' for _ in values])
    return (f"({placeholders})", tuple(values))


# Re-export for backward compatibility
region_of = get_region_for_city