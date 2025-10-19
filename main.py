# main.py
"""
Main entry point for the Geographical Expense Analysis System.
Initializes the agent and runs test queries.
"""
import os
import sys
import logging
from typing import Callable, Any

# CRITICAL: Add project root to sys.path for module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_community.llms import Ollama
from langchain_core.exceptions import OutputParserException

# Import the semantic layer generator
from semantic_layer.generate_semantic_layer import generate_semantic_layer_file

# Import the agent creation function
from agents.hardcoded_agent import create_hardcoded_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

LLM_MODEL_NAME = os.getenv("OLLAMA_MODEL", "mistral:latest")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))


def run_agent_test(query: str, agent: Callable[[str], str]) -> None:
    """
    Invokes the agent with a query and displays results.
    
    Args:
        query: User's natural language query
        agent: The agent invocation function
    """
    print(f"\n{'='*70}")
    print(f"USER QUERY: {query}")
    print('='*70)
    
    try:
        # Invoke the agent
        result = agent(query)
        
        if result:
            print(f"\n{result}")
        else:
            print("\n❌ AGENT RESPONSE: Received an empty result.")
            
    except OutputParserException as e:
        # LLM failed to produce structured output
        logger.warning("LLM did not produce structured output")
        print(f"\n⚠️  WARNING: The LLM output could not be parsed.")
        print(f"   This is expected for out-of-scope queries.")
        raw_output = getattr(e, 'llm_output', 'N/A')
        print(f"   RAW LLM OUTPUT: {raw_output[:200]}...")
        
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        print(f"\n❌ CRITICAL ERROR during agent execution: {e}")
        print("   Check database connection and configuration.")


def initialize_system() -> bool:
    """
    Performs initial system setup and validation.
    
    Returns:
        True if initialization successful, False otherwise
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
        print(f"\n❌ FATAL ERROR: Semantic Layer Generation Failed")
        print(f"   Details: {e}")
        print(f"   Check database credentials in config/mariadb_config.py")
        return False
    
    # Step 2: Verify Ollama connection
    print("\nSTEP 2: Verifying Ollama Connection...")
    try:
        test_llm = Ollama(
            model=LLM_MODEL_NAME, 
            base_url=OLLAMA_BASE_URL,
            temperature=OLLAMA_TEMPERATURE
        )
        # Quick test
        test_llm.invoke("test")
        print(f"✅ Connected to Ollama (model: {LLM_MODEL_NAME})")
    except Exception as e:
        logger.error(f"Ollama connection failed: {e}", exc_info=True)
        print(f"\n❌ FATAL ERROR: Could not connect to Ollama")
        print(f"   Details: {e}")
        print(f"\nPlease ensure:")
        print(f"   1. Ollama is running: Check {OLLAMA_BASE_URL}")
        print(f"   2. Model is downloaded: ollama pull {LLM_MODEL_NAME}")
        print(f"   3. Model name is correct: {LLM_MODEL_NAME}")
        return False
    
    return True


def main():
    """Main execution function"""
    
    # Initialize system
    if not initialize_system():
        print("\n❌ System initialization failed. Exiting.")
        sys.exit(1)
    
    # Create LLM client
    print(f"\nSTEP 3: Initializing Agent...")
    try:
        llm_client = Ollama(
            model=LLM_MODEL_NAME,
            base_url=OLLAMA_BASE_URL,
            temperature=OLLAMA_TEMPERATURE
        )
        logger.info(f"LLM client initialized: {LLM_MODEL_NAME}")
    except Exception as e:
        logger.error(f"Failed to create LLM client: {e}")
        print(f"\n❌ FATAL ERROR: Could not create LLM client: {e}")
        sys.exit(1)
    
    # Create agent
    try:
        hardcoded_agent = create_hardcoded_agent(llm_client=llm_client)
        print(f"✅ Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to create agent: {e}", exc_info=True)
        print(f"\n❌ FATAL ERROR: Could not create agent: {e}")
        sys.exit(1)
    
    # Interactive mode
    print("\n" + "="*70)
    print("  INTERACTIVE QUERY MODE")
    print("="*70)
    print("\nYou can now ask questions about geographical expenses.")
    print("\nExample queries:")
    print("  • What are the total expenses for WEST region?")
    print("  • Give me the total spend for warehouses in GURUGRAM")
    print("  • Calculate expenses for warehouse SURAT-2")
    print("  • Show me expenses for NORTH region")
    print("\nType 'quit', 'exit', or 'q' to stop.")
    print("Type 'test' to run automated test suite.")
    print("="*70 + "\n")
    
    query_count = 0
    
    while True:
        try:
            # Get user input
            user_query = input("\n💬 Enter your query: ").strip()
            
            # Check for exit commands
            if user_query.lower() in ['quit', 'exit', 'q', '']:
                print("\n👋 Goodbye!")
                break
            
            # Check for test command
            if user_query.lower() == 'test':
                run_test_suite(hardcoded_agent)
                continue
            
            # Process the query
            query_count += 1
            print(f"\n[QUERY #{query_count}]")
            run_agent_test(user_query, hardcoded_agent)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted. Type 'quit' to exit or continue querying.")
            continue
        except EOFError:
            print("\n\n👋 Goodbye!")
            break
    
    # Summary
    if query_count > 0:
        print("\n" + "="*70)
        print(f"  SESSION SUMMARY: {query_count} queries processed")
        print("="*70)


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