# agents/hardcoded_agent.py
"""
LLM-powered agent for parsing user queries and executing geographical expense calculations.
Uses Ollama for local LLM inference to extract filter parameters from natural language.
"""
import json
import logging
from typing import Dict, Any, Optional
from langchain_community.llms import Ollama

from tools.hardcoded_query import calculate_geographical_expenses

logger = logging.getLogger(__name__)

# System prompt for the LLM - defines strict JSON output format
SYSTEM_PROMPT = """You are a specialized JSON extraction engine for geographical expense queries.

Your ONLY task is to analyze user queries and output a single JSON object with exactly two fields:
- filter_type: Must be one of "REGION", "CITY", or "WAREHOUSE" (or null if query is out of scope)
- filter_value: The exact name or code mentioned (e.g., "NORTH", "DELHI", "DELHI-123")

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown, no code blocks, no explanations
2. Use null values for both fields if the query is not about geographical expenses
3. Extract the exact spelling and capitalization from the user's query
4. Common regions: NORTH, SOUTH, EAST, WEST

Valid output examples:
{"filter_type": "REGION", "filter_value": "NORTH"}
{"filter_type": "CITY", "filter_value": "DELHI"}
{"filter_type": "WAREHOUSE", "filter_value": "DELHI-123"}
{"filter_type": null, "filter_value": null}
"""


def create_hardcoded_agent(llm_client: Ollama):
    """
    Factory function that creates and returns the agent invocation function.
    
    Args:
        llm_client: Initialized Ollama LLM client
        
    Returns:
        Function that processes user queries and returns results
    """
    
    def agent_invoke(user_query: str) -> str:
        """
        Processes a user query through the LLM and executes the appropriate tool.
        
        Args:
            user_query: Natural language query from the user
            
        Returns:
            Formatted string with results or error message
            
        Process:
            1. Format prompt with system instructions and user query
            2. Get LLM response (should be JSON)
            3. Parse JSON to extract filter_type and filter_value
            4. Call calculate_geographical_expenses tool
            5. Return formatted results
        """
        logger.info(f"Processing query: {user_query[:100]}...")
        
        # Step 1: Build the prompt using structured format
        prompt = f"""### SYSTEM INSTRUCTION
{SYSTEM_PROMPT}

### USER QUERY
{user_query}

### OUTPUT (JSON only)
"""
        
        try:
            # Step 2: Get LLM response
            response = llm_client.invoke(prompt)
            logger.debug(f"Raw LLM response: {response}")
            
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            return f"❌ Error: Failed to communicate with LLM: {e}"
        
        # Step 3: Parse JSON response
        try:
            # Clean common LLM formatting issues
            cleaned_response = response.strip()
            
            # Remove markdown code blocks if present
            if cleaned_response.startswith("```"):
                lines = cleaned_response.split('\n')
                # Remove first and last lines (```json and ```)
                cleaned_response = '\n'.join(lines[1:-1])
            
            # Remove any "json" prefix
            cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()
            
            # Parse the JSON
            parsed = json.loads(cleaned_response)
            
            filter_type = parsed.get("filter_type")
            filter_value = parsed.get("filter_value")
            
            logger.info(f"Extracted: filter_type='{filter_type}', filter_value='{filter_value}'")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Problematic response: {response}")
            return (
                f"❌ Invalid LLM output (JSON parsing failed)\n"
                f"Error: {e}\n"
                f"LLM returned: {response[:200]}"
            )
        except Exception as e:
            logger.error(f"Unexpected parsing error: {e}")
            return f"❌ Error parsing LLM response: {e}"
        
        # Step 4: Validate extracted parameters
        if not filter_type or not filter_value:
            logger.info("Query determined to be out of scope")
            return (
                "⚠️ Query is out of scope or cannot be processed.\n"
                "This agent can only calculate expenses by REGION, CITY, or WAREHOUSE.\n"
                "Examples:\n"
                "  - 'What are total expenses for NORTH region?'\n"
                "  - 'Show me expenses for DELHI city'\n"
                "  - 'Calculate costs for warehouse DELHI-1'"
            )
        
        # Validate filter_type
        valid_types = ["REGION", "CITY", "WAREHOUSE"]
        if filter_type.upper() not in valid_types:
            return (
                f"❌ Invalid filter type: '{filter_type}'\n"
                f"Must be one of: {', '.join(valid_types)}"
            )
        
        # Step 5: Execute the tool
        try:
            logger.info(f"Executing tool with filter_type='{filter_type}', filter_value='{filter_value}'")
            result = calculate_geographical_expenses(
                filter_type=filter_type,
                filter_value=filter_value
            )
            
            # Format success message
            if result.startswith("ERROR"):
                return f"❌ {result}"
            elif result.startswith("INFO"):
                return f"⚠️ {result}"
            else:
                return f"✅ SUCCESS\n\n{result}"
                
        except Exception as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            return f"❌ Tool execution error: {e}"
    
    return agent_invoke


def create_agent_with_config(
    model_name: str = "llama2",
    base_url: str = "http://localhost:11434",
    temperature: float = 0.1
) -> callable:
    """
    Convenience function to create an agent with custom configuration.
    
    Args:
        model_name: Name of the Ollama model to use
        base_url: URL of the Ollama server
        temperature: LLM temperature (lower = more deterministic)
        
    Returns:
        Configured agent invocation function
    """
    logger.info(f"Initializing agent with model '{model_name}'")
    
    try:
        llm = Ollama(
            model=model_name,
            base_url=base_url,
            temperature=temperature
        )
        
        agent = create_hardcoded_agent(llm)
        logger.info("Agent initialized successfully")
        return agent
        
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create agent
    agent = create_agent_with_config(model_name="llama2")
    
    # Test queries
    test_queries = [
        "What are the total expenses for NORTH region?",
        "Show me costs for DELHI city",
        "Calculate expenses for warehouse DELHI-1",
        "What is the weather today?",  # Out of scope
    ]
    
    print("\n" + "="*80)
    print("TESTING HARDCODED AGENT")
    print("="*80 + "\n")
    
    for query in test_queries:
        print(f"\nQUERY: {query}")
        print("-" * 80)
        result = agent(query)
        print(result)
        print("\n")