# semantic_layer/generate_semantic_layer.py
"""
Generates a semantic layer JSON file by extracting database schema metadata
and enriching it with business-friendly descriptions for LLM consumption.
"""
import os
import json
import logging
from typing import Dict, List, Any
import mariadb

from config.mariadb_config import get_db_config

logger = logging.getLogger(__name__)

# Tables to include in the semantic layer
INVOICE_POC_TABLES = [
    "invoice_info",
    "warehouse_info",
]


def extract_raw_metadata(db_config: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """
    Extracts raw schema metadata from INFORMATION_SCHEMA for specified tables.
    
    Args:
        db_config: Database configuration dictionary
        
    Returns:
        Dictionary mapping table names to their column metadata
        
    Security:
        Uses parameterized queries to prevent SQL injection
    """
    raw_schema = {}
    db_name = db_config["database"]
    
    logger.info(f"Connecting to database '{db_name}' to extract metadata...")
    
    conn = None
    try:
        conn = mariadb.connect(**db_config)
        cursor = conn.cursor()
        
        for table_name in INVOICE_POC_TABLES:
            # SECURE: Using parameterized query
            query = """
                SELECT 
                    COLUMN_NAME, 
                    DATA_TYPE, 
                    COLUMN_KEY, 
                    IS_NULLABLE 
                FROM 
                    INFORMATION_SCHEMA.COLUMNS 
                WHERE 
                    TABLE_SCHEMA = ? 
                    AND TABLE_NAME = ?
                ORDER BY 
                    ORDINAL_POSITION;
            """
            
            cursor.execute(query, (db_name, table_name))
            results = cursor.fetchall()
            
            column_details = []
            for row in results:
                column_details.append({
                    "name": row[0],
                    "data_type": row[1],
                    "is_key": row[2] if len(row) > 2 else None,
                    "nullable": row[3] if len(row) > 3 else None
                })
            
            if column_details:
                raw_schema[table_name] = column_details
                logger.info(f"Extracted schema for '{table_name}': {len(column_details)} columns")
            else:
                logger.warning(f"No columns found for table '{table_name}'")

    except mariadb.Error as e:
        logger.error(f"Database error during metadata extraction: {e}")
        return {}
        
    except Exception as e:
        logger.error(f"Unexpected error during metadata extraction: {e}")
        return {}
        
    finally:
        if conn:
            conn.close()

    logger.info(f"Successfully extracted metadata for {len(raw_schema)} tables")
    return raw_schema


def llm_generate_descriptions(raw_schema: Dict[str, List[Dict]]) -> Dict:
    """
    Enriches raw schema with business-friendly descriptions.
    
    In production, this would call an LLM API. For now, it uses predefined
    business descriptions that help the agent understand the data model.
    
    Args:
        raw_schema: Raw schema metadata from database
        
    Returns:
        Semantic layer dictionary with tables, columns, and relationships
    """
    semantic_layer = {
        "tables": [],
        "relationships": [],
        "metadata": {
            "generated_from": list(raw_schema.keys()),
            "version": "1.0"
        }
    }
    
    # Table: invoice_info
    if 'invoice_info' in raw_schema:
        semantic_layer['tables'].append({
            "name": "invoice_info",
            "description": (
                "Core invoice transaction table. Contains expense amounts and "
                "links to warehouse locations. Use this table to calculate total "
                "expenses and spending patterns."
            ),
            "columns": [
                {
                    "name": "id",
                    "description": "Unique invoice identifier (Primary Key). Auto-incrementing integer.",
                    "semantic_type": "identifier"
                },
                {
                    "name": "warehouse_id",
                    "description": (
                        "Foreign key linking to warehouse_info.id. CRITICAL for "
                        "geographical expense analysis and regional reporting."
                    ),
                    "semantic_type": "foreign_key",
                    "references": "warehouse_info.id"
                },
                {
                    "name": "invoice_date",
                    "description": (
                        "Date the invoice was generated. Use for time-series analysis "
                        "and period-based expense reports."
                    ),
                    "semantic_type": "date"
                },
                {
                    "name": "total_amount",
                    "description": (
                        "Final monetary amount including GST. THIS IS THE PRIMARY "
                        "METRIC for all expense calculations and aggregations."
                    ),
                    "semantic_type": "currency",
                    "aggregations": ["SUM", "AVG", "MIN", "MAX"]
                },
            ]
        })
    
    # Table: warehouse_info
    if 'warehouse_info' in raw_schema:
        semantic_layer['tables'].append({
            "name": "warehouse_info",
            "description": (
                "Warehouse location master data. Maps warehouse IDs to geographical "
                "locations via warehouse codes. Essential for region/city-based filtering."
            ),
            "columns": [
                {
                    "name": "id",
                    "description": "Unique warehouse identifier (Primary Key). Links to invoice_info.warehouse_id.",
                    "semantic_type": "identifier"
                },
                {
                    "name": "warehouse_code",
                    "description": (
                        "Standardized location code in format: CITY-NUMBER (e.g., 'DELHI-1', "
                        "'CHARKHI DADRI-65'). The city prefix MUST be extracted for regional "
                        "classification. This is the KEY field for geographical analysis."
                    ),
                    "semantic_type": "location_code",
                    "format": "CITY-NUMBER"
                },
                {
                    "name": "warehouse_name",
                    "description": "Human-readable warehouse name for display purposes.",
                    "semantic_type": "text"
                },
            ]
        })

    # Relationships
    semantic_layer['relationships'].extend([
        {
            "description": "Links invoices to their warehouse location",
            "type": "MANY_TO_ONE",
            "from_table": "invoice_info",
            "from_column": "warehouse_id",
            "to_table": "warehouse_info",
            "to_column": "id",
            "join_condition": "invoice_info.warehouse_id = warehouse_info.id"
        },
    ])
    
    # Add business rules
    semantic_layer['business_rules'] = [
        {
            "rule": "geographical_filtering",
            "description": (
                "To filter by REGION or CITY, you must: "
                "1. Query warehouse_info to get warehouse codes "
                "2. Extract city names from warehouse_code (everything before last hyphen) "
                "3. Map cities to regions using the region mapping system "
                "4. Filter warehouse IDs based on the geographical criteria "
                "5. Use filtered warehouse_ids in invoice_info query"
            )
        },
        {
            "rule": "expense_calculation",
            "description": (
                "Always use SUM(total_amount) from invoice_info for expense totals. "
                "The total_amount field already includes GST - do not apply additional tax calculations."
            )
        }
    ]

    return semantic_layer


def generate_semantic_layer_file(output_filename: str = "invoices_semantic_layer.json") -> bool:
    """
    Main function to generate and save the semantic layer JSON file.
    
    Args:
        output_filename: Name of the output JSON file
        
    Returns:
        True if generation was successful, False otherwise
    """
    logger.info("Starting semantic layer generation process...")
    
    try:
        # Get database configuration
        db_config = get_db_config("INVOICES")
        
        # Step 1: Extract raw metadata from database
        raw_data = extract_raw_metadata(db_config)
        
        if not raw_data:
            logger.error("Failed to extract any metadata from database")
            return False
        
        # Step 2: Enrich with business descriptions
        final_semantic_layer = llm_generate_descriptions(raw_data)
        
        # Step 3: Save to file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(base_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_semantic_layer, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Successfully generated semantic layer: {output_path}")
        logger.info(f"Tables included: {', '.join(raw_data.keys())}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate semantic layer: {e}")
        return False


def validate_semantic_layer(filepath: str) -> bool:
    """
    Validates that a semantic layer file exists and has valid structure.
    
    Args:
        filepath: Path to the semantic layer JSON file
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if not os.path.exists(filepath):
            logger.error(f"Semantic layer file not found: {filepath}")
            return False
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check required structure
        required_keys = {"tables", "relationships"}
        if not all(key in data for key in required_keys):
            logger.error("Semantic layer missing required keys")
            return False
        
        # Validate tables
        if not isinstance(data["tables"], list) or len(data["tables"]) == 0:
            logger.error("Semantic layer has no tables defined")
            return False
        
        logger.info(f"Semantic layer validation passed: {filepath}")
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in semantic layer: {e}")
        return False
    except Exception as e:
        logger.error(f"Error validating semantic layer: {e}")
        return False


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    success = generate_semantic_layer_file()
    
    if success:
        print("\n✅ Semantic layer generation completed successfully!")
    else:
        print("\n❌ Semantic layer generation failed. Check logs for details.")