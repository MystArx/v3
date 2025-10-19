#!/usr/bin/env python3
"""
Quick start script to test your Geographical Expense Analysis System.
Run this after installation to verify everything works.
"""

import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_section(title):
    """Print a section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def test_imports():
    """Test that all required modules can be imported"""
    print_section("STEP 1: Testing Imports")
    
    try:
        import mariadb
        logger.info("✅ mariadb imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import mariadb: {e}")
        logger.error("   Install with: pip install mariadb")
        return False
    
    try:
        from langchain_community.llms import Ollama
        logger.info("✅ langchain_community imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import langchain_community: {e}")
        logger.error("   Install with: pip install langchain-community")
        return False
    
    try:
        from config.mariadb_config import DB_CONNECTION_MAP
        logger.info("✅ config.mariadb_config imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import config: {e}")
        logger.error("   Make sure you're running from the v1 directory")
        return False
    
    try:
        from tools.region_map import REGION_MAP, get_region_for_city
        logger.info("✅ tools.region_map imported successfully")
        logger.info(f"   Loaded {len(REGION_MAP)} city mappings")
    except ImportError as e:
        logger.error(f"❌ Failed to import tools.region_map: {e}")
        return False
    
    try:
        from tools.core_tools import sql_executor
        logger.info("✅ tools.core_tools imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import tools.core_tools: {e}")
        return False
    
    try:
        from tools.hardcoded_query import calculate_geographical_expenses
        logger.info("✅ tools.hardcoded_query imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import tools.hardcoded_query: {e}")
        return False
    
    return True

def test_database_connection():
    """Test database connectivity"""
    print_section("STEP 2: Testing Database Connections")
    
    from config.mariadb_config import DB_CONNECTION_MAP
    import mariadb
    
    for db_name, config in DB_CONNECTION_MAP.items():
        try:
            conn = mariadb.connect(**config)
            conn.close()
            logger.info(f"✅ Successfully connected to {db_name} database")
        except mariadb.Error as e:
            logger.error(f"❌ Failed to connect to {db_name}: {e}")
            logger.error(f"   Check credentials in config/mariadb_config.py")
            return False
    
    return True

def test_region_mapping():
    """Test region mapping functionality"""
    print_section("STEP 3: Testing Region Mapping")
    
    from tools.region_map import get_region_for_city, get_all_regions
    
    # Test some cities
    test_cities = ["DELHI", "MUMBAI", "BANGALORE", "KOLKATA"]
    
    for city in test_cities:
        region = get_region_for_city(city)
        if region != "REGION_UNKNOWN":
            logger.info(f"✅ {city} -> {region}")
        else:
            logger.warning(f"⚠️  {city} not found in region map")
    
    regions = get_all_regions()
    logger.info(f"\nTotal regions configured: {regions}")
    
    return True

def test_warehouse_query():
    """Test warehouse query execution"""
    print_section("STEP 4: Testing Warehouse Query")
    
    from tools.core_tools import sql_executor
    
    query = "SELECT COUNT(*) FROM warehouse_info;"
    result = sql_executor(query, "WAREHOUSE")
    
    if result.startswith("ERROR"):
        logger.error(f"❌ Warehouse query failed: {result}")
        return False
    
    logger.info("✅ Warehouse query executed successfully")
    print(f"Result:\n{result}")
    return True

def test_invoice_query():
    """Test invoice query execution"""
    print_section("STEP 5: Testing Invoice Query")
    
    from tools.core_tools import sql_executor
    
    query = "SELECT COUNT(*) FROM invoice_info;"
    result = sql_executor(query, "INVOICES")
    
    if result.startswith("ERROR"):
        logger.error(f"❌ Invoice query failed: {result}")
        return False
    
    logger.info("✅ Invoice query executed successfully")
    print(f"Result:\n{result}")
    return True

def test_geographical_calculation():
    """Test the main geographical expense calculation"""
    print_section("STEP 6: Testing Geographical Expense Calculation")
    
    from tools.hardcoded_query import calculate_geographical_expenses
    
    # Test by region
    logger.info("Testing REGION filter...")
    result = calculate_geographical_expenses("REGION", "NORTH")
    
    if result.startswith("ERROR"):
        logger.error(f"❌ Regional calculation failed: {result}")
        return False
    
    logger.info("✅ Regional calculation successful")
    print(f"Result:\n{result}\n")
    
    return True

def test_ollama_connection():
    """Test Ollama LLM connection"""
    print_section("STEP 7: Testing Ollama Connection (Optional)")
    
    model = "mistral:latest"
    
    try:
        from langchain_community.llms import Ollama
        
        llm = Ollama(model=model, temperature=0.1)
        response = llm.invoke("Say 'test successful' and nothing else.")
        
        logger.info("✅ Ollama connection successful")
        logger.info(f"   Response: {response[:100]}")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️  Ollama connection failed: {e}")
        logger.warning("   This is optional. Install Ollama from https://ollama.ai")
        logger.warning(f"   Then run: ollama pull {model}")
        return None  # None means optional test

def test_agent():
    """Test the full agent pipeline"""
    print_section("STEP 8: Testing Full Agent (Optional)")
    
    try:
        from agents.hardcoded_agent import create_agent_with_config
        
        agent = create_agent_with_config(model_name="llama2")
        
        test_query = "What are the total expenses for NORTH region?"
        logger.info(f"Query: {test_query}")
        
        result = agent(test_query)
        logger.info("✅ Agent execution successful")
        print(f"Result:\n{result}\n")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️  Agent test failed: {e}")
        logger.warning("   Requires Ollama to be running")
        return None  # None means optional test

def main():
    """Run all tests"""
    print("\n" + "🚀 " * 20)
    print("    GEOGRAPHICAL EXPENSE ANALYSIS SYSTEM - QUICK START")
    print("🚀 " * 20)
    
    results = {
        "Imports": test_imports(),
        "Database Connection": test_database_connection(),
        "Region Mapping": test_region_mapping(),
        "Warehouse Query": test_warehouse_query(),
        "Invoice Query": test_invoice_query(),
        "Geographical Calculation": test_geographical_calculation(),
        "Ollama Connection": test_ollama_connection(),
        "Full Agent": test_agent(),
    }
    
    # Summary
    print_section("FINAL SUMMARY")
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for test_name, result in results.items():
        if result is True:
            print(f"✅ {test_name}: PASSED")
        elif result is False:
            print(f"❌ {test_name}: FAILED")
        else:
            print(f"⚠️  {test_name}: SKIPPED (optional)")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed == 0:
        print("\n🎉 All required tests passed! Your system is ready to use.")
        print("\nNext steps:")
        print("  1. Review the README.md for usage examples")
        print("  2. Try running: python agents/hardcoded_agent.py")
        print("  3. Start building your application!")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        print("\nCommon solutions:")
        print("  - Install missing packages: pip install -r requirements.txt")
        print("  - Check database credentials in config/mariadb_config.py")
        print("  - Ensure databases exist and have data")
        return 1

if __name__ == "__main__":
    sys.exit(main())
    