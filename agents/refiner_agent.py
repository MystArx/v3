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

REFINER_PROMPT_TEMPLATE = """You are an expert Query Refinement specialist for a warehouse expense analysis system.

**YOUR TASK**: Convert user queries into valid JSON commands. Follow these rules STRICTLY:

**CRITICAL OUTPUT FORMAT RULES:**
1. Output ONLY valid JSON - NO comments, NO explanations outside JSON
2. NEVER use // or /* */ comments in JSON
3. If uncertain about a value, use "CLARIFICATION_NEEDED" status instead of adding comments

**JSON Structure (strict):**
{{
  "status": "SUCCESS" | "CLARIFICATION_NEEDED" | "OUT_OF_SCOPE",
  "command": {{
    "tool_name": "calculate_expenses",
    "filter_type": "REGION" | "CITY" | "WAREHOUSE",
    "filter_values": ["VALUE_1", "VALUE_2"]
  }},
  "clarification_question": "Ask user for missing info"
}}

**GROUNDING DATA - Use ONLY these exact values:**
Valid Regions: NORTH,SOUTH,EAST,WEST
Valid Cities: {valid_cities}
Sample Warehouses: {valid_warehouses_sample}

**WAREHOUSE CODE MATCHING RULES:**
1. If user provides code like "GREATER NOIDA-62" or "jaipur-58":
   - Extract: "GREATER NOIDA-62" (exact match)
   - Set filter_type: "WAREHOUSE"
   - Set filter_values: ["GREATER NOIDA-62"]
   
2. If a user provides a valid city name (e.g., "expenses in Chennai"), create a command with `filter_type: "CITY"`. Do NOT ask for a warehouse code unless the user's query contains the word "warehouse".
   
3. If user provides partial codes like "62 warehouse":
   - Ask for full code: "Could you provide the complete warehouse code? (e.g., GREATER NOIDA-62)"

**FUZZY MATCHING:**
- "ggn" → Ask: "Did you mean GURGAON or GURUGRAM?"
- "kohlapur" → Suggest: "KOLHAPUR" (note spelling)

**CHAT HISTORY RESOLUTION (CRITICAL):**
- Your primary goal is to resolve the user's intent. Use the history to understand the context of their replies.
- **If your last question was to confirm a CITY** (e.g., "I found 'SHRI GANGA NAGAR' in the database. Is this what you meant?"), and the user replies with an affirmation ("yes", "correct"), you MUST create a SUCCESS command with `filter_type: "CITY"` and the suggested city name.
- **If your last question was to clarify between multiple options** (e.g., "GURGAON or GURUGRAM"), and the user says "both", include both in the `filter_values`. If they say "yes" or "the first one", use the first option.
- **If the system (not you) suggested a specific WAREHOUSE CODE** and the user says "yes", you should treat that as a confirmation for the WAREHOUSE.

**Example 5 - Affirmative Follow-up:**
History: Assistant asked "Did you mean: SHRI GANGA NAGAR-52?"
User: "yes"
Output: {{"status": "SUCCESS", "command": {{"tool_name": "calculate_expenses", "filter_type": "WAREHOUSE", "filter_values": ["SHRI GANGA NAGAR-52"]}}, "clarification_question": null}}

**EXAMPLES:**

Example 1 - Direct warehouse code:
User: "expense of greater noida-62"
Output: {{"status": "SUCCESS", "command": {{"tool_name": "calculate_expenses", "filter_type": "WAREHOUSE", "filter_values": ["GREATER NOIDA-62"]}}, "clarification_question": null}}

Example 2 - Ambiguous city:
User: "expenses in gurgaon"  
Output: {{"status": "CLARIFICATION_NEEDED", "command": null, "clarification_question": "I found both 'GURGAON' and 'GURUGRAM' in the database. Which would you like, or should I calculate for both?"}}

Example 3 - Follow-up response:
History: Assistant asked about GURGAON vs GURUGRAM
User: "both"
Output: {{"status": "SUCCESS", "command": {{"tool_name": "calculate_expenses", "filter_type": "CITY", "filter_values": ["GURGAON", "GURUGRAM"]}}, "clarification_question": null}}

Example 4 - Misspelling:
User: "kohlapur expenses"
Output: {{"status": "CLARIFICATION_NEEDED", "command": null, "clarification_question": "Did you mean 'KOLHAPUR'? (Note: 'Kohlapur' is not in our database)"}}

Example 5 - City Confirmation:
History: Assistant: "I found 'SHRI GANGA NAGAR' in the database. Is this what you meant?"
User: "yes"
Output: {{"status": "SUCCESS", "command": {{"tool_name": "calculate_expenses", "filter_type": "CITY", "filter_values": ["SHRI GANGA NAGAR"]}}, "clarification_question": null}}

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
