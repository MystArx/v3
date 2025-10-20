# agents/refiner_agent.py
"""
IMPROVED LLM-powered agent for refining and clarifying user queries.
V2 fixes: JSON comment issues, better warehouse code handling, fuzzy matching
"""
import json
import re
import logging
from typing import Dict, Any, List
from langchain_community.llms import Ollama
from difflib import get_close_matches

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REFINER_PROMPT_TEMPLATE = """You are an expert Query Refinement specialist for a warehouse analysis system.

**YOUR TASK**: Convert user queries into valid JSON commands. Follow these rules STRICTLY:

**CRITICAL OUTPUT FORMAT RULES:**
1. Output ONLY valid JSON - NO comments, NO explanations outside JSON.
2. If uncertain, use "CLARIFICATION_NEEDED" status.

---

### **TOOL SELECTION LOGIC**
- **Default to `calculate_expenses`** for any query about totals, costs, or spending.
- Use **`list_warehouses_by_location`** if the user asks to "list", "show", or "find" warehouses in a CITY or REGION.
- Use **`get_warehouse_details`** if the user asks for "address", "pincode", "location", or "details" of a specific warehouse.
- Use **`find_warehouse_by_address`** ONLY if the user's query contains specific street names or landmarks.

---

### **JSON STRUCTURE (Strict and Unified for all tools)**
{{
  "status": "SUCCESS" | "CLARIFICATION_NEEDED" | "OUT_OF_SCOPE",
  "command": {{
    "tool_name": "calculate_expenses" | "list_warehouses_by_location" | "get_warehouse_details" | "find_warehouse_by_address",
    "filter_type": "REGION" | "CITY" | "WAREHOUSE" | "WAREHOUSE_IDENTIFIER" | "ADDRESS_KEYWORD",
    "filter_values": ["VALUE_1", "VALUE_2"]
  }},
  "clarification_question": "Ask user for missing info"
}}

---

### **GROUNDING DATA - Use ONLY these exact values:**
Valid Regions: NORTH,SOUTH,EAST,WEST
Valid Cities: {valid_cities}
Sample Warehouses: {valid_warehouses_sample}

---

### **CHAT HISTORY RESOLUTION (CRITICAL):**
- **Most Important Rule:** If the last assistant message was a suggestion starting with "💡 Did you mean:", and the user replies with an affirmation ("yes", "correct", "that's the one"), you MUST create a SUCCESS command using the first warehouse code from the suggestion.
- **If your last question confirmed a CITY** (e.g., "I found 'SHRI GANGA NAGAR'... Is this what you meant?"), and the user says "yes", the tool should be `list_warehouses_by_location` for that CITY.
- **If the user says "both"** after you suggest multiple cities, include both in the `filter_values`.
- **If the last suggestion was a list of warehouse codes for a city** (e.g., "...Did you mean: KOLKATA-74, KOLKATA-73?"), and the user replies with just a number (e.g., "75"), you MUST infer the full warehouse code by combining the city from the previous context with the new number (e.g., "KOLKATA-75").

---

### **EXAMPLES**

**-- Expense Calculation --**
User: "expense of greater noida-62"
Output: {{"status": "SUCCESS", "command": {{"tool_name": "calculate_expenses", "filter_type": "WAREHOUSE", "filter_values": ["GREATER NOIDA-62"]}}, "clarification_question": null}}

**-- Warehouse Listing & Details --**
User: "show me all warehouses in the NORTH region"
Output: {{"status": "SUCCESS", "command": {{"tool_name": "list_warehouses_by_location", "filter_type": "REGION", "filter_values": ["NORTH"]}}, "clarification_question": null}}

User: "what is the address for GURGAON-9"
Output: {{"status": "SUCCESS", "command": {{"tool_name": "get_warehouse_details", "filter_type": "WAREHOUSE_IDENTIFIER", "filter_values": ["GURGAON-9"]}}, "clarification_question": null}}

User: "find a warehouse on udyog vihar"
Output: {{"status": "SUCCESS", "command": {{"tool_name": "find_warehouse_by_address", "filter_type": "ADDRESS_KEYWORD", "filter_values": ["udyog vihar"]}}, "clarification_question": null}}

**-- Critical History Example --**
History: Assistant: "⚠️ Invalid WAREHOUSE values: ['SONIPAT']\\n   💡 Did you mean: SONIPAT-4?"
User: "yes"
Output: {{"status": "SUCCESS", "command": {{"tool_name": "get_warehouse_details", "filter_type": "WAREHOUSE_IDENTIFIER", "filter_values": ["SONIPAT-4"]}}, "clarification_question": null}}

**-- Critical History Example 2 (Numerical Follow-up) --**
History: Assistant: "⚠️ Invalid WAREHOUSE values: ['KOLKATA']\\n   💡 Did you mean: KOLKATA-74, KOLKATA-73, KOLKATA-13?"
User: "75"
Output: {{"status": "SUCCESS", "command": {{"tool_name": "get_warehouse_details", "filter_type": "WAREHOUSE_IDENTIFIER", "filter_values": ["KOLKATA-75"]}}, "clarification_question": null}}
---

### **CURRENT CONVERSATION**
**CHAT HISTORY:**
{chat_history}

**CURRENT USER QUERY:**
{user_query}

**OUTPUT (pure JSON only, no comments):**
"""


def fuzzy_match_city(user_input: str, valid_cities: List[str], threshold: float = 0.6) -> List[str]:
    """
    Finds close matches for user input among valid cities.
    
    Args:
        user_input: User's city name input
        valid_cities: List of valid city names
        threshold: Similarity threshold (0-1)
    
    Returns:
        List of matching city names
    """
    matches = get_close_matches(user_input.upper(), valid_cities, n=3, cutoff=threshold)
    return matches


def extract_warehouse_code_from_query(query: str, valid_warehouses: List[str]) -> str | None:
    """
    Attempts to extract a valid warehouse code from the user query,
    handling both space and hyphen separators.
    """
    query_upper = query.upper().strip()

    # Create a potential code from the query by replacing the last space with a hyphen
    # This handles "CHENNAI 16" -> "CHENNAI-16"
    if ' ' in query_upper and query_upper.split(' ')[-1].isdigit():
        parts = query_upper.rsplit(' ', 1)
        potential_code_from_space = f"{parts[0]}-{parts[1]}"
        if potential_code_from_space in valid_warehouses:
            return potential_code_from_space

    # Direct exact match (handles "CHENNAI-16")
    for warehouse in valid_warehouses:
        if warehouse in query_upper:
            return warehouse

    # Original pattern match for safety
    pattern = r'([A-Z\s]+)-(\d+)'
    match = re.search(pattern, query_upper)
    if match:
        potential_code = f"{match.group(1).strip()}-{match.group(2)}"
        if potential_code in valid_warehouses:
            return potential_code
            
    return None

def clean_json_response(response: str) -> str:
    """
    Removes JSON comments and cleans LLM response.
    
    Args:
        response: Raw LLM response
    
    Returns:
        Cleaned JSON string
    """
    # Remove markdown code blocks
    cleaned = response.strip().replace("```json", "").replace("```", "").strip()
    
    # Remove single-line comments (// ...)
    cleaned = re.sub(r'//.*?(?=\n|$)', '', cleaned)
    
    # Remove multi-line comments (/* ... */)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    
    # Remove trailing commas before closing braces/brackets
    cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
    
    return cleaned.strip()


def create_refiner_agent(llm_client: Ollama):
    """Factory function for the stateful, grounded refiner agent."""

    def agent_invoke(
        user_query: str,
        chat_history: List[Dict[str, str]],
        valid_regions: List[str],
        valid_cities: List[str],
        valid_warehouses: List[str]
    ) -> Dict[str, Any]:
        
        logger.info(f"Refining query: '{user_query}' with history length: {len(chat_history or [])}")

        # Pre-processing: Check for direct warehouse code match
        warehouse_match = extract_warehouse_code_from_query(user_query, valid_warehouses)
        if warehouse_match:
            logger.info(f"Direct warehouse code match found: {warehouse_match}")
            return {
                "status": "SUCCESS",
                "command": {
                    "tool_name": "calculate_expenses",
                    "filter_type": "WAREHOUSE",
                    "filter_values": [warehouse_match]
                },
                "clarification_question": None
            }

        # Format chat history
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history]) if chat_history else "No history yet."
        
        # Sample warehouses for prompt (avoid overwhelming)
        warehouses_sample = valid_warehouses[:15]

        prompt = REFINER_PROMPT_TEMPLATE.format(
            valid_regions=valid_regions,
            valid_cities=valid_cities,
            valid_warehouses_sample=warehouses_sample,
            chat_history=history_str,
            user_query=user_query
        )

        try:
            response = llm_client.invoke(prompt)
            logger.debug(f"Raw LLM response: {response}")
            
            cleaned_response = clean_json_response(response)
            logger.debug(f"Cleaned response: {cleaned_response}")
            
            parsed_json = json.loads(cleaned_response)
            
            # Validate the parsed JSON structure
            if "status" not in parsed_json:
                raise ValueError("Missing 'status' field in LLM response")
            
            logger.info(f"Refined output: {parsed_json}")
            return parsed_json
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed for response: {response}", exc_info=True)
            
            # Fallback: Try fuzzy matching on the original query
            fuzzy_matches = fuzzy_match_city(user_query, valid_cities, threshold=0.7)
            if fuzzy_matches:
                return {
                    "status": "CLARIFICATION_NEEDED",
                    "command": None,
                    "clarification_question": f"Did you mean one of these cities: {', '.join(fuzzy_matches)}?"
                }
            
            return {
                "status": "ERROR",
                "error_message": f"Failed to parse LLM response. JSON error: {e}"
            }
            
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}", exc_info=True)
            return {
                "status": "ERROR",
                "error_message": f"LLM invocation failed: {e}"
            }

    return agent_invoke
