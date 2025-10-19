# main.py
"""
Main entry point for the Geographical Expense Analysis System.
Orchestrates the stateful two-agent workflow, manages chat history,
and grounds the refiner agent with validated data.
"""
import os
import sys
import logging
from typing import Callable, Any, Dict, List

# CRITICAL: Add project root to sys.path for module imports
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


def run_executor_agent(command: Dict[str, Any], agent: Callable[[Dict[str, Any]], str]) -> str:
    """
    Invokes the executor agent and returns the result string.
    """
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
    """
    print("\n" + "- "*25)
    print("  JARVIS V3")
    print("- "*25 + "\n")
    
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
        test_llm.invoke("test")
        print(f"✅ Connected to Ollama (model: {LLM_MODEL_NAME})")
    except Exception as e:
        logger.error(f"Ollama connection failed: {e}", exc_info=True)
        print(f"\n❌ FATAL ERROR: Could not connect to Ollama: {e}")
        return False
        
    # Step 3: Initialize Data Validator
    print("\nSTEP 3: Initializing Data Validator...")
    try:
        data_validator.initialize()
        print("✅ Data Validator initialized successfully.")
    except Exception as e:
        logger.error(f"Data Validator initialization failed: {e}", exc_info=True)
        print(f"\n❌ FATAL ERROR: Could not initialize Data Validator: {e}")
        return False
    
    return True


def main():
    """Main execution function with chat history management."""
    
    if not initialize_system():
        print("\n❌ System initialization failed. Exiting.")
        sys.exit(1)
    
    print(f"\nSTEP 4: Initializing Agents...")
    try:
        llm_client = Ollama(model=LLM_MODEL_NAME, base_url=OLLAMA_BASE_URL, temperature=OLLAMA_TEMPERATURE)
        refiner_agent = create_refiner_agent(llm_client=llm_client)
        executor_agent = create_executor_agent()
        print(f"✅ Agents initialized successfully")
    except Exception as e:
        logger.error(f"Failed to create agents: {e}", exc_info=True)
        sys.exit(1)
    
    print("\n" + "="*70)
    print("  INTERACTIVE QUERY MODE (Grounded with Memory)")
    print("="*70)
    print("\nYou can now have a conversation about geographical expenses.")
    print("Type 'quit' or 'exit' to stop.")
    print("="*70 + "\n")
    
    chat_history: List[Dict[str, str]] = []
    
    # Get valid values once to pass to the agent
    valid_regions = data_validator.get_valid_regions()
    valid_cities = data_validator.get_valid_cities()
    valid_warehouses = data_validator.get_valid_warehouses()

    while True:
        try:
            user_query = input("\n💬 User: ").strip()
            if user_query.lower() in ['quit', 'exit', 'q', '', 'bye']:
                print("\n👋 Goodbye!")
                break

            # Step 1: Call the Refiner Agent with the current query, history, and validated data
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
            
            else:
                error_msg = refinement_result.get("error_message", "An unknown error occurred.")
                print(f"\n❌ ERROR: {error_msg}")

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted. Type 'quit' to exit.")
            continue
        except EOFError:
            print("\n\n👋 Goodbye!")
            break

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