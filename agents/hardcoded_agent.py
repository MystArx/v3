# agents/hardcoded_agent.py
"""
The Executor Agent for geographical expense calculations.
This agent does NOT use an LLM. It directly executes a structured command
that has been cleaned and validated by the Refiner Agent.
"""
import logging
from typing import Dict, Any
from tools.hardcoded_query import calculate_geographical_expenses

logger = logging.getLogger(__name__)


def create_executor_agent():
    """
    Factory function that creates and returns the executor agent invocation function.
    This agent is deterministic and does not need an LLM client.
    """
    
    def agent_invoke(command: Dict[str, Any]) -> str:
        """
        Executes a pre-validated command to calculate expenses.
        
        Args:
            command: A dictionary containing 'tool_name', 'filter_type', and 'filter_values'.
            
        Returns:
            A formatted string with the results or an error message.
        """
        logger.info(f"Executing command: {command}")
        
        if not command or command.get("tool_name") != "calculate_expenses":
            return "❌ ERROR: Invalid command received by executor agent."
            
        filter_type = command.get("filter_type")
        filter_values = command.get("filter_values")

        if not filter_type or not filter_values:
            return "❌ ERROR: Command is missing 'filter_type' or 'filter_values'."

        # Validate filter_type
        valid_types = ["REGION", "CITY", "WAREHOUSE"]
        if filter_type.upper() not in valid_types:
            return (
                f"❌ Invalid filter type: '{filter_type}'\n"
                f"Must be one of: {', '.join(valid_types)}"
            )
        
        # Execute the tool with the correct parameters
        try:
            logger.info(f"Executing tool with filter_type='{filter_type}', filter_values='{filter_values}'")
            result = calculate_geographical_expenses(
                filter_type=filter_type,
                filter_values=filter_values  # Pass the list of values
            )
            
            # Format the final result message
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


# Example usage for standalone testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create the executor agent
    executor = create_executor_agent()
    
    # Test command for a single value
    print("\n--- Testing Single Value ---")
    single_value_command = {
        "tool_name": "calculate_expenses",
        "filter_type": "CITY",
        "filter_values": ["DELHI"]
    }
    print(executor(single_value_command))

    # Test command for multiple values
    print("\n--- Testing Multiple Values ---")
    multi_value_command = {
        "tool_name": "calculate_expenses",
        "filter_type": "REGION",
        "filter_values": ["NORTH", "WEST"]
    }
    print(executor(multi_value_command))

