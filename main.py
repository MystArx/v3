# main.py
"""
IMPROVED main entry point with better error handling and validation reporting.
V2 improvements: Pre-flight checks, validation report, graceful fallbacks
"""
import os
import sys
import logging
from typing import Callable, Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_community.llms import Ollama
from semantic_layer.generate_semantic_layer import generate_semantic_layer_file
from agents.refiner_agent import create_refiner_agent
from agents.hardcoded_agent import create_executor_agent
from tools.data_validator import data_validator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

LLM_MODEL_NAME = os.getenv("OLLAMA_MODEL", "mistral:latest")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))


def print_banner():
    """Prints application banner."""
    print("\n" + "🚀 " * 25)
    print("  JARVIS V3 - Geographical Expense Analysis System")
    print("  IMPROVED VERSION with Enhanced Validation")
    print("🚀 " * 25 + "\n")


def run_executor_agent(command: Dict[str, Any], agent: Callable[[Dict[str, Any]], str]) -> str:
    """Invokes the executor agent and returns the result string."""
    print(f"\n{'='*70}")
    print(f"EXECUTING COMMAND: {command}")
    print('='*70)
    
    try:
        result = agent(command)
        if result:
            print(f"\n{result}")
            return result
        else:
            error_msg = "\n❌ AGENT RESPONSE: Received an empty result."
            print(error_msg)
            return error_msg
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        error_msg = f"\n❌ CRITICAL ERROR during agent execution: {e}"
        print(error_msg)
        return error_msg


def initialize_system() -> bool:
    """
    Performs initial system setup and validation.
    Returns True if successful, False otherwise.
    """
    print_banner()
    
    # Step 1: Generate semantic layer
    print("STEP 1: Generating Semantic Layer...")
    try:
        success = generate_semantic_layer_file()
        if success:
            print("✅ Semantic layer generated successfully")
        else:
            print("❌ Semantic layer generation failed")
            return False
    except Exception as e:
        logger.error(f"Semantic layer generation failed: {e}", exc_info=True)
        print(f"\n❌ FATAL ERROR: Semantic Layer Generation Failed: {e}")
        return False
    
    # Step 2: Verify Ollama connection
    print("\nSTEP 2: Verifying Ollama Connection...")
    try:
        test_llm = Ollama(
            model=LLM_MODEL_NAME, 
            base_url=OLLAMA_BASE_URL,
            temperature=OLLAMA_TEMPERATURE
        )
        test_response = test_llm.invoke("test")
        print(f"✅ Connected to Ollama (model: {LLM_MODEL_NAME})")
        logger.debug(f"Test response: {test_response[:50]}...")
    except Exception as e:
        logger.error(f"Ollama connection failed: {e}", exc_info=True)
        print(f"\n❌ FATAL ERROR: Could not connect to Ollama: {e}")
        print("   Make sure Ollama is running: ollama serve")
        print(f"   And model is pulled: ollama pull {LLM_MODEL_NAME}")
        return False
        
    # Step 3: Initialize Data Validator
    print("\nSTEP 3: Initializing Data Validator...")
    try:
        data_validator.initialize()
        print("✅ Data Validator initialized successfully.")
        
        # Print validation summary
        regions = data_validator.get_valid_regions()
        cities = data_validator.get_valid_cities()
        warehouses = data_validator.get_valid_warehouses()
        
        print(f"   📊 Loaded: {len(regions)} regions, {len(cities)} cities, {len(warehouses)} warehouses")
        
        # Check for common issues
        if len(cities) == 0:
            print("   ⚠️  WARNING: No cities found in database!")
            return False
            
        if len(warehouses) == 0:
            print("   ⚠️  WARNING: No warehouses found in database!")
            return False
            
    except Exception as e:
        logger.error(f"Data Validator initialization failed: {e}", exc_info=True)
        print(f"\n❌ FATAL ERROR: Could not initialize Data Validator: {e}")
        return False
    
    # Step 4: Run validation checks
    print("\nSTEP 4: Running Data Validation Checks...")
    try:
        # Check for common misspellings
        problematic_cities = []
        for city in cities:
            if city.lower().startswith('koh'):
                problematic_cities.append(city)
        
        if problematic_cities:
            print(f"   ⚠️  Found potential spelling issues: {problematic_cities}")
            print("   💡 TIP: Run fix_database.py to correct these")
        else:
            print("   ✅ No obvious data issues found")
            
    except Exception as e:
        logger.warning(f"Validation checks encountered errors: {e}")
    
    return True


def display_help():
    """Displays available commands and tips."""
    help_text = """
╔════════════════════════════════════════════════════════════════════╗
║                        JARVIS V3 - HELP                            ║
╚════════════════════════════════════════════════════════════════════╝

QUERY EXAMPLES:
  • "expenses in NORTH region"
  • "total for Mumbai"
  • "warehouse DELHI-1"
  • "expenses for GURGAON and GURUGRAM"
  • "all warehouses in Bangalore"

WAREHOUSE CODE FORMAT:
  • Format: CITY-NUMBER (e.g., GREATER NOIDA-62)
  • Always use the full code for specific warehouses

SPECIAL COMMANDS:
  • 'help' - Show this help message
  • 'report' - Display data validation report
  • 'quit' or 'exit' - Exit the application

TIPS:
  • I'll ask for clarification if your query is ambiguous
  • Use exact city/region names for best results
  • Type 'both' to include multiple options when asked

═══════════════════════════════════════════════════════════════════════
"""
    print(help_text)


def main():
    """Main execution function with chat history management."""
    
    if not initialize_system():
        print("\n❌ System initialization failed. Exiting.")
        sys.exit(1)
    
    print(f"\nSTEP 5: Initializing Agents...")
    try:
        llm_client = Ollama(model=LLM_MODEL_NAME, base_url=OLLAMA_BASE_URL, temperature=OLLAMA_TEMPERATURE)
        refiner_agent = create_refiner_agent(llm_client=llm_client)
        executor_agent = create_executor_agent()
        print(f"✅ Agents initialized successfully")
    except Exception as e:
        logger.error(f"Failed to create agents: {e}", exc_info=True)
        print(f"\n❌ FATAL ERROR: Could not initialize agents: {e}")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("  INTERACTIVE QUERY MODE")
    print("="*70)
    print("\nReady to analyze geographical expenses!")
    print("Type 'help' for examples, 'quit' to exit.")
    print("="*70 + "\n")
    
    chat_history: List[Dict[str, str]] = []
    
    # Get valid values once to pass to the agent
    valid_regions = data_validator.get_valid_regions()
    valid_cities = data_validator.get_valid_cities()
    valid_warehouses = data_validator.get_valid_warehouses()

    while True:
        try:
            user_query = input("\n💬 User: ").strip()
            
            # Handle special commands
            if user_query.lower() in ['quit', 'exit', 'q', 'bye']:
                print("\n👋 Goodbye!")
                break
            
            if not user_query:
                continue
                
            if user_query.lower() == 'help':
                display_help()
                continue
                
            if user_query.lower() == 'report':
                print(data_validator.get_report())
                continue

            # Step 1: Call the Refiner Agent
            refinement_result = refiner_agent(
                user_query, 
                chat_history,
                valid_regions,
                valid_cities,
                valid_warehouses
            )
            
            status = refinement_result.get("status")

            # Step 2: Act based on the refinement status
            if status == "SUCCESS":
                command = refinement_result.get("command")
                
                # Validate command before execution
                filter_type = command.get("filter_type")
                filter_values = command.get("filter_values", [])
                
                # Pre-execution validation
                invalid_values = []
                if filter_type == "REGION":
                    invalid_values = [v for v in filter_values if not data_validator.validate_region(v)]
                elif filter_type == "CITY":
                    invalid_values = [v for v in filter_values if not data_validator.validate_city(v)]
                elif filter_type == "WAREHOUSE":
                    invalid_values = [v for v in filter_values if not data_validator.validate_warehouse(v)]
                
                if invalid_values:
                    error_msg = f"⚠️  Invalid {filter_type} values: {invalid_values}"
                    print(f"\n{error_msg}")
                    
                    # Suggest corrections
                    for inv_val in invalid_values:
                        if filter_type == "CITY":
                            suggestions = data_validator.fuzzy_match_city(inv_val)
                        elif filter_type == "WAREHOUSE":
                            suggestions = data_validator.fuzzy_match_warehouse(inv_val)
                        else:
                            suggestions = []
                        
                        if suggestions:
                            print(f"   💡 Did you mean: {', '.join(suggestions[:3])}?")
                    
                    chat_history.append({"role": "user", "content": user_query})
                    chat_history.append({"role": "assistant", "content": error_msg})
                    continue
                
                # Execute the command
                final_result = run_executor_agent(command, executor_agent)
                chat_history.append({"role": "user", "content": user_query})
                chat_history.append({"role": "assistant", "content": final_result})
            
            elif status == "CLARIFICATION_NEEDED":
                clarification = refinement_result.get("clarification_question")
                print(f"\n🤔 Assistant: {clarification}")
                chat_history.append({"role": "user", "content": user_query})
                chat_history.append({"role": "assistant", "content": clarification})
            
            elif status == "OUT_OF_SCOPE":
                response = "\n⚠️  INFO: This query is out of scope. I can only answer questions about expenses."
                print(response)
                chat_history.append({"role": "user", "content": user_query})
                chat_history.append({"role": "assistant", "content": response})
            
            elif status == "ERROR":
                error_msg = refinement_result.get("error_message", "An unknown error occurred.")
                print(f"\n❌ ERROR: {error_msg}")
                
                # Offer fallback suggestions
                print("\n💡 Try:")
                print("   • Use exact city/region names")
                print("   • For warehouses, use format: CITY-NUMBER")
                print("   • Type 'help' for examples")

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted. Type 'quit' to exit.")
            continue
        except EOFError:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            print(f"\n❌ UNEXPECTED ERROR: {e}")
            print("💡 The system is still running. Try another query or type 'quit' to exit.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unexpected error in main: {e}", exc_info=True)
        print(f"\n❌ CRITICAL ERROR: {e}")
        sys.exit(1)