# agents/hardcoded_agent.py
"""
The Executor Agent for geographical expense calculations.
This agent does NOT use an LLM. It directly executes a structured command
that has been cleaned and validated by the Refiner Agent.
"""
import logging
from typing import Dict, Any
from tools.hardcoded_query import calculate_geographical_expenses
from tools.warehouse_tools import (
    list_warehouses_by_location,
    find_warehouse_by_address,
    get_warehouse_details
)

logger = logging.getLogger(__name__)


# agents/hardcoded_agent.py
"""
The Executor Agent for all warehouse-related queries.
This agent does NOT use an LLM. It routes a structured command from the
Refiner Agent to the appropriate tool function.
"""
import logging
from typing import Dict, Any, Callable # <-- Added Callable for type hinting

# Import all tool functions
from tools.hardcoded_query import calculate_geographical_expenses
from tools.warehouse_tools import (
    list_warehouses_by_location,
    find_warehouse_by_address,
    get_warehouse_details,
)

logger = logging.getLogger(__name__)


def create_executor_agent() -> Callable[[Dict[str, Any]], str]:
    """
    Factory function that creates and returns the executor agent invocation function.
    This agent is deterministic and does not need an LLM client.
    """

    def agent_invoke(command: Dict[str, Any]) -> str:
        """
        Executes a pre-validated command by routing it to the correct tool.

        Args:
            command: A dictionary containing 'tool_name', 'filter_type', and 'filter_values'.

        Returns:
            A formatted string with the results or an error message.
        """
        logger.info(f"Executing command: {command}")

        tool_name = command.get("tool_name")
        filter_type = command.get("filter_type")
        filter_values = command.get("filter_values")

        if not all([tool_name, filter_type, filter_values]):
            return "❌ ERROR: Command is missing 'tool_name', 'filter_type', or 'filter_values'."

        try:
            result = ""
            # --- Tool Routing Logic ---
            if tool_name == "calculate_expenses":
                logger.info(f"Routing to 'calculate_expenses' with filter: {filter_type}")
                result = calculate_geographical_expenses(
                    filter_type=filter_type,
                    filter_values=filter_values
                )
            elif tool_name == "list_warehouses_by_location":
                logger.info(f"Routing to 'list_warehouses_by_location' with filter: {filter_type}")
                result = list_warehouses_by_location(
                    filter_type=filter_type,
                    filter_values=filter_values
                )
            elif tool_name == "get_warehouse_details":
                logger.info(f"Routing to 'get_warehouse_details'")
                # This tool expects a single identifier
                result = get_warehouse_details(warehouse_identifier=filter_values[0])
            elif tool_name == "find_warehouse_by_address":
                logger.info(f"Routing to 'find_warehouse_by_address'")
                # This tool expects a single keyword
                result = find_warehouse_by_address(address_keyword=filter_values[0])
            else:
                return f"❌ ERROR: Unknown tool_name '{tool_name}' received by executor."

            # --- Unified Result Formatting ---
            if result.startswith("ERROR"):
                return f"❌ {result}"
            elif result.startswith("INFO"):
                return f"⚠️ {result}"
            else:
                return f"✅ SUCCESS\n\n{result}"

        except IndexError:
            logger.error(f"Tool '{tool_name}' was called with missing filter_values.")
            return f"❌ ERROR: The command for '{tool_name}' requires a value but received none."
        except Exception as e:
            logger.error(f"Tool execution failed for '{tool_name}': {e}", exc_info=True)
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

    # --- Test 1: Existing Expense Calculation (No breaking change) ---
    print("\n--- Testing: calculate_expenses ---")
    expense_command = {
        "tool_name": "calculate_expenses",
        "filter_type": "CITY",
        "filter_values": ["DELHI"]
    }
    print(executor(expense_command))

    # --- Test 2: New - List Warehouses by Location ---
    print("\n--- Testing: list_warehouses_by_location ---")
    list_command = {
        "tool_name": "list_warehouses_by_location",
        "filter_type": "REGION",
        "filter_values": ["SOUTH"]
    }
    print(executor(list_command))
    
    # --- Test 3: New - Get Specific Warehouse Details ---
    print("\n--- Testing: get_warehouse_details ---")
    details_command = {
        "tool_name": "get_warehouse_details",
        "filter_type": "WAREHOUSE_IDENTIFIER",
        "filter_values": ["GURGAON-9"]
    }
    print(executor(details_command))

    # --- Test 4: New - Find Warehouse by Address Keyword ---
    print("\n--- Testing: find_warehouse_by_address ---")
    address_command = {
        "tool_name": "find_warehouse_by_address",
        "filter_type": "ADDRESS_KEYWORD",
        "filter_values": ["Udyog Vihar"]
    }
    print(executor(address_command))
