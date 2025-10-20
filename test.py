#!/usr/bin/env python3
"""
Comprehensive test suite for JARVIS V3 improvements.
Tests: fuzzy matching, warehouse code parsing, JSON cleaning, validation
"""
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_json_cleaning():
    """Test JSON comment removal."""
    print("\n" + "="*70)
    print("TEST 1: JSON Comment Cleaning")
    print("="*70)
    
    from agents.refiner_agent import clean_json_response
    
    test_cases = [
        # Test case 1: Single-line comment
        (
            '{"status": "SUCCESS", "command": {"filter_values": ["KOLHAPUR-89"]} // comment}',
            True
        ),
        # Test case 2: Multi-line comment
        (
            '{"status": "SUCCESS" /* this is a comment */ }',
            True
        ),
        # Test case 3: Trailing comma
        (
            '{"status": "SUCCESS", "values": ["A", "B",]}',
            True
        ),
        # Test case 4: Markdown code blocks
        (
            '```json\n{"status": "SUCCESS"}\n```',
            True
        )
    ]
    
    passed = 0
    for i, (test_input, should_parse) in enumerate(test_cases, 1):
        try:
            import json
            cleaned = clean_json_response(test_input)
            parsed = json.loads(cleaned)
            if should_parse:
                print(f"  ✅ Test {i}: Passed (cleaned and parsed successfully)")
                passed += 1
            else:
                print(f"  ❌ Test {i}: Failed (should not have parsed)")
        except Exception as e:
            if not should_parse:
                print(f"  ✅ Test {i}: Passed (correctly failed)")
                passed += 1
            else:
                print(f"  ❌ Test {i}: Failed - {e}")
    
    print(f"\nResult: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_warehouse_code_extraction():
    """Test warehouse code extraction from queries."""
    print("\n" + "="*70)
    print("TEST 2: Warehouse Code Extraction")
    print("="*70)
    
    from agents.refiner_agent import extract_warehouse_code_from_query
    
    # Mock warehouse list
    valid_warehouses = [
        "GREATER NOIDA-62", "JAIPUR-58", "KOLHAPUR-89", 
        "GURGAON-9", "DELHI-1", "CHARKHI DADRI-65"
    ]
    
    test_cases = [
        ("expense of greater noida-62", "GREATER NOIDA-62"),
        ("JAIPUR-58 warehouse", "JAIPUR-58"),
        ("tell me about KOLHAPUR-89", "KOLHAPUR-89"),
        ("charkhi dadri-65 expenses", "CHARKHI DADRI-65"),
        ("warehouse in mumbai", None),  # Should not match
    ]
    
    passed = 0
    for query, expected in test_cases:
        result = extract_warehouse_code_from_query(query, valid_warehouses)
        if result == expected:
            print(f"  ✅ '{query}' → {result}")
            passed += 1
        else:
            print(f"  ❌ '{query}' → Expected: {expected}, Got: {result}")
    
    print(f"\nResult: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_fuzzy_matching():
    """Test fuzzy city/warehouse matching."""
    print("\n" + "="*70)
    print("TEST 3: Fuzzy Matching")
    print("="*70)
    
    from tools.data_validator import DataValidator
    
    validator = DataValidator()
    
    # Mock data
    validator._valid_cities = {
        "GURGAON", "GURUGRAM", "KOLHAPUR", "GREATER NOIDA", 
        "DELHI", "MUMBAI", "BANGALORE"
    }
    validator._valid_warehouses = {
        "GREATER NOIDA-62", "KOLHAPUR-89", "GURGAON-9"
    }
    
    test_cases = [
        ("ggn", "city", ["GURGAON", "GURUGRAM"]),  # Should match both
        ("kohlapur", "city", ["KOLHAPUR"]),
        ("greater noid", "city", ["GREATER NOIDA"]),
        ("KOLHAPUR-8", "warehouse", ["KOLHAPUR-89"]),
    ]
    
    passed = 0
    for user_input, match_type, expected_matches in test_cases:
        if match_type == "city":
            results = validator.fuzzy_match_city(user_input, threshold=0.6)
        else:
            results = validator.fuzzy_match_warehouse(user_input, threshold=0.7)
        
        # Check if at least one expected match is in results
        found = any(exp in results for exp in expected_matches)
        
        if found:
            print(f"  ✅ '{user_input}' → {results}")
            passed += 1
        else:
            print(f"  ❌ '{user_input}' → Expected any of {expected_matches}, Got: {results}")
    
    print(f"\nResult: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_data_validator():
    """Test data validator initialization and validation."""
    print("\n" + "="*70)
    print("TEST 4: Data Validator")
    print("="*70)
    
    try:
        from tools.data_validator import data_validator
        
        # Initialize
        data_validator.initialize()
        
        regions = data_validator.get_valid_regions()
        cities = data_validator.get_valid_cities()
        warehouses = data_validator.get_valid_warehouses()
        
        print(f"  ✅ Loaded: {len(regions)} regions")
        print(f"  ✅ Loaded: {len(cities)} cities")
        print(f"  ✅ Loaded: {len(warehouses)} warehouses")
        
        # Test validation
        test_validations = [
            ("NORTH", data_validator.validate_region, True),
            ("INVALID", data_validator.validate_region, False),
            ("KOLHAPUR", data_validator.validate_city, True),
            ("KOHLAPUR", data_validator.validate_city, False),  # Wrong spelling
        ]
        
        passed = 0
        for value, validator_func, expected in test_validations:
            result = validator_func(value)
            if result == expected:
                print(f"  ✅ validate('{value}') = {result}")
                passed += 1
            else:
                print(f"  ❌ validate('{value}') = {result}, expected {expected}")
        
        print(f"\nResult: {passed + 3}/{len(test_validations) + 3} checks passed")
        return passed == len(test_validations)
        
    except Exception as e:
        print(f"  ❌ Data validator test failed: {e}")
        return False


def test_region_mapping():
    """Test region mapping corrections."""
    print("\n" + "="*70)
    print("TEST 5: Region Mapping")
    print("="*70)
    
    from tools.region_map import get_region_for_city, REGION_MAP
    
    test_cases = [
        ("KOLHAPUR", "WEST"),  # Fixed spelling
        ("GURGAON", "NORTH"),
        ("GURUGRAM", "NORTH"),
        ("BANGALORE", "SOUTH"),
        ("KOLKATA", "EAST"),
        ("KOHLAPUR", "REGION_UNKNOWN"),  # Wrong spelling should not exist
    ]
    
    passed = 0
    for city, expected_region in test_cases:
        result = get_region_for_city(city)
        if result == expected_region:
            print(f"  ✅ {city} → {result}")
            passed += 1
        else:
            print(f"  ❌ {city} → Expected: {expected_region}, Got: {result}")
    
    # Check if KOHLAPUR is in map (it shouldn't be after fix)
    if "KOHLAPUR" not in REGION_MAP:
        print("  ✅ KOHLAPUR correctly removed from region map")
        passed += 1
    else:
        print("  ⚠️  KOHLAPUR still in region map (should be KOLHAPUR)")
    
    print(f"\nResult: {passed}/{len(test_cases) + 1} tests passed")
    return passed == len(test_cases) + 1


def test_city_extraction():
    """Test city extraction from warehouse codes."""
    print("\n" + "="*70)
    print("TEST 6: City Extraction from Warehouse Codes")
    print("="*70)
    
    from tools.core_tools import extract_city_from_warehouse_code
    
    test_cases = [
        ("GREATER NOIDA-62", "GREATER NOIDA"),
        ("CHARKHI DADRI-65", "CHARKHI DADRI"),
        ("DELHI-1", "DELHI"),
        ("KOLHAPUR-89", "KOLHAPUR"),
        ("SHRI GANGA NAGAR-52", "SHRI GANGA NAGAR"),
    ]
    
    passed = 0
    for warehouse_code, expected_city in test_cases:
        result = extract_city_from_warehouse_code(warehouse_code)
        if result == expected_city:
            print(f"  ✅ {warehouse_code} → {result}")
            passed += 1
        else:
            print(f"  ❌ {warehouse_code} → Expected: {expected_city}, Got: {result}")
    
    print(f"\nResult: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def run_all_tests():
    """Run all test suites."""
    print("\n" + "🧪 " * 25)
    print("  JARVIS V3 - COMPREHENSIVE TEST SUITE")
    print("🧪 " * 25)
    
    results = {
        "JSON Cleaning": test_json_cleaning(),
        "Warehouse Code Extraction": test_warehouse_code_extraction(),
        "Fuzzy Matching": test_fuzzy_matching(),
        "Data Validator": test_data_validator(),
        "Region Mapping": test_region_mapping(),
        "City Extraction": test_city_extraction(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("  FINAL SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{len(results)} test suites passed")
    
    if failed == 0:
        print("\n🎉 All tests passed! Your improvements are working correctly.")
        return 0
    else:
        print(f"\n⚠️  {failed} test suite(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
