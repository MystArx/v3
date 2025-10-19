# tools/region_map.py
"""
City-to-region mapping system with JSON persistence.
Provides centralized region lookup for geographical expense calculations.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Default region mappings - serves as fallback and documentation
_DEFAULT_REGION_MAP: Dict[str, str] = {
    # NORTH REGION
    "ALWAR": "NORTH", "AMBALA": "NORTH", "BAHADURGARH": "NORTH", 
    "BAMNOLI": "NORTH", "BAREILLY": "NORTH", "BAWAL": "NORTH", 
    "CHARKHI DADRI": "NORTH", "DHARUHERA": "NORTH", "FARIDABAD": "NORTH", 
    "FAROOQNAGAR": "NORTH", "GHAZIABAD": "NORTH", "GREATER NOIDA": "NORTH",
    "GURGAON": "NORTH", "GURUGRAM": "NORTH", "HAPUR": "NORTH", 
    "HARIDWAR": "NORTH", "JAIPUR": "NORTH", "JHAJJAR": "NORTH", 
    "KARNAL": "NORTH", "LUCKNOW": "NORTH", "MANESAR": "NORTH", 
    "MERTA CITY": "NORTH", "MOHALI": "NORTH", "PATAUDI": "NORTH",
    "RAJPURA": "NORTH", "REWARI": "NORTH", "SHRI GANGA NAGAR": "NORTH", 
    "SONIPAT": "NORTH", "UDAIPURI": "NORTH",
    
    # EAST REGION
    "ASANSOL": "EAST", "BHUBANESWAR": "EAST", "GUWAHATI": "EAST", 
    "KOLKATA": "EAST", "PATNA": "EAST", "RANCHI": "EAST",
    
    # WEST REGION
    "AHMEDABAD": "WEST", "BHIWANDI": "WEST", "INDORE": "WEST",
    "KOHLAPUR": "WEST", "RAJKOT": "WEST", "SURAT": "WEST",
    
    # SOUTH REGION
    "BANGALORE": "SOUTH", "CHENNAI": "SOUTH", "COIMBATORE": "SOUTH", 
    "HYDERABAD": "SOUTH", "MADURAI": "SOUTH", "TIRUPATI": "SOUTH", 
    "TRICHY": "SOUTH"
}


def load_region_map() -> Dict[str, str]:
    """
    Loads region map from region_map.json, falling back to defaults if needed.
    
    Returns:
        Dictionary mapping city names (uppercase) to region names
        
    Notes:
        - Always returns a valid dictionary (never fails)
        - JSON file is optional - defaults are always available
        - JSON entries override defaults
        - All keys are normalized to uppercase
    """
    # Start with complete default map
    region_map = _DEFAULT_REGION_MAP.copy()
    
    # Try to load and merge JSON file
    json_path = Path(__file__).with_suffix('.json')
    
    if not json_path.exists():
        logger.info(f"Region map JSON not found at {json_path}, using defaults")
        return region_map
    
    try:
        with json_path.open('r', encoding='utf-8') as fh:
            json_data = json.load(fh)
            
        # Merge JSON data, normalizing keys to uppercase
        for city, region in json_data.items():
            normalized_city = str(city).strip().upper()
            normalized_region = str(region).strip().upper()
            region_map[normalized_city] = normalized_region
            
        logger.info(f"Loaded {len(json_data)} city mappings from {json_path}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in region map file: {e}. Using defaults.")
    except Exception as e:
        logger.error(f"Failed to load region map: {e}. Using defaults.")
    
    return region_map


# Load the region map at module initialization
REGION_MAP = load_region_map()


def get_region_for_city(city: str, default: str = "REGION_UNKNOWN") -> str:
    """
    Returns the region for a given city name.
    
    Args:
        city: City name (case-insensitive, will be normalized)
        default: Value to return if city is not found
        
    Returns:
        Region name (e.g., 'NORTH', 'SOUTH', 'EAST', 'WEST') or default
        
    Examples:
        >>> get_region_for_city('delhi')
        'NORTH'
        >>> get_region_for_city('Mumbai')
        'REGION_UNKNOWN'
    """
    if not city:
        return default
    
    # Normalize the city name for lookup
    normalized_city = city.strip().upper()
    region = REGION_MAP.get(normalized_city, default)
    
    if region == default:
        logger.debug(f"City not found in region map: {city}")
    
    return region


def region_of(city: str) -> str:
    """
    Alias for get_region_for_city for backward compatibility.
    
    Args:
        city: City name
        
    Returns:
        Region name or 'REGION_UNKNOWN'
    """
    return get_region_for_city(city)


def get_all_regions() -> set:
    """Returns set of all unique region names in the map."""
    return set(REGION_MAP.values())


def get_cities_by_region(region: str) -> list:
    """
    Returns list of all cities in a given region.
    
    Args:
        region: Region name (case-insensitive)
        
    Returns:
        List of city names in that region
    """
    normalized_region = region.strip().upper()
    return [
        city for city, reg in REGION_MAP.items() 
        if reg == normalized_region
    ]


def add_city_mapping(city: str, region: str) -> bool:
    """
    Adds a new city-region mapping to the runtime map.
    Note: This does NOT persist to JSON file.
    
    Args:
        city: City name
        region: Region name
        
    Returns:
        True if added successfully
    """
    try:
        normalized_city = city.strip().upper()
        normalized_region = region.strip().upper()
        REGION_MAP[normalized_city] = normalized_region
        logger.info(f"Added mapping: {normalized_city} -> {normalized_region}")
        return True
    except Exception as e:
        logger.error(f"Failed to add city mapping: {e}")
        return False