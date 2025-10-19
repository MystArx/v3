# agents/refiner_agent.py
"""
LLM-powered agent for refining and clarifying user queries about expenses.
This version is grounded with valid data from the database to improve accuracy
and uses chat history to resolve conversational context.
"""
import json
import logging
from typing import Dict, Any, List
from langchain_community.llms import Ollama

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# This prompt is now a template that will be filled with valid data
REFINER_PROMPT_TEMPLATE = """You are a world-class Query Refinement specialist. Your goal is to analyze a user's request and transform it into a structured, valid JSON command. You MUST ground your answers in the provided lists of valid values.

Your JSON output MUST have the following structure:
{{
  "status": "SUCCESS" | "CLARIFICATION_NEEDED" | "OUT_OF_SCOPE",
  "command": {{
    "tool_name": "calculate_expenses",
    "filter_type": "REGION" | "CITY" | "WAREHOUSE",
    "filter_values": ["VALUE_1", "VALUE_2", ...]
  }} | null,
  "clarification_question": "A question to ask the user" | null
}}

**GROUNDING DATA (Use these exact values):**
- Valid Regions: {valid_regions}
- Valid Cities: {valid_cities}
- A small sample of valid Warehouses: {valid_warehouses_sample}

**CRITICAL RULES:**
1.  **Strict Validation**: The values in `filter_values` MUST exist in the corresponding 'Valid' lists above. Do not invent or guess values. If a user's term (e.g., "ggn") doesn't match a valid City or Warehouse, ask for clarification.
2.  **Tool Name is Fixed**: The `tool_name` MUST ALWAYS be "calculate_expenses". Do not use any other tool name.
3.  **Use Chat History**: If the 'CURRENT USER QUERY' is a short follow-up like "both" or "just the first one," you MUST use the 'CHAT HISTORY' to understand the original question and provide a complete, new command.
4.  **Handle "Gurgaon" Ambiguity**: The user might say "Gurgaon", but the database contains both "GURGAON" and "GURUGRAM". If the user asks for "Gurgaon", you MUST ask for clarification. The only exception is if they say "both" in response to that specific question.
5.  **Conversational Resolution Example**:
    - History: `Assistant: I found entries for both 'Gurgaon' and 'Gurugram'. Which one would you like to see, or should I calculate for both?`
    - Current Query: `both`
    - Your Output: A SUCCESS status with `filter_values` of `["GURGAON", "GURUGRAM"]`.

### CHAT HISTORY
{chat_history}

### CURRENT USER QUERY
{user_query}

### OUTPUT (JSON only)
"""

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

        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history]) if chat_history else "No history yet."
        
        # To avoid overwhelming the prompt, we only include a small sample of warehouses
        warehouses_sample = valid_warehouses[:10]

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
            cleaned_response = response.strip().replace("```json", "").replace("```", "").strip()
            parsed_json = json.loads(cleaned_response)
            logger.info(f"Refined output: {parsed_json}")
            return parsed_json
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed for response: {response}", exc_info=True)
            return {"status": "ERROR", "error_message": f"Failed to parse LLM JSON output: {e}"}
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}", exc_info=True)
            return {"status": "ERROR", "error_message": f"LLM invocation failed: {e}"}

    return agent_invoke

