"""
Test LangSmith integration.

This script verifies that LangSmith tracing is working correctly.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_langsmith_connection():
    """Test LangSmith API connection."""
    print("Testing LangSmith connection...")
    
    # Check environment variables
    tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    api_key = os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGCHAIN_PROJECT", "recruitment-agent")
    
    print(f"  LANGCHAIN_TRACING_V2: {tracing_enabled}")
    print(f"  LANGCHAIN_API_KEY: {'***' + api_key[-10:] if api_key else 'NOT SET'}")
    print(f"  LANGCHAIN_PROJECT: {project}")
    
    if not tracing_enabled:
        print("\n❌ LangSmith tracing is disabled")
        print("   Set LANGCHAIN_TRACING_V2=true in .env to enable")
        return False
    
    if not api_key:
        print("\n❌ LangSmith API key not found")
        print("   Set LANGCHAIN_API_KEY in .env")
        return False
    
    # Try to connect to LangSmith
    try:
        from langsmith import Client
        client = Client()
        print(f"\n✓ LangSmith client initialized successfully")
        print(f"  Project: {project}")
        print(f"  Endpoint: {os.getenv('LANGCHAIN_ENDPOINT', 'https://api.smith.langchain.com')}")
        return True
    except Exception as e:
        print(f"\n❌ Failed to initialize LangSmith client: {e}")
        return False


def test_simple_trace():
    """Test creating a simple trace."""
    print("\n\nTesting simple trace creation...")
    
    try:
        from langsmith import traceable
        
        @traceable(name="test_function")
        def simple_function(x: int, y: int) -> int:
            """A simple function to test tracing."""
            return x + y
        
        result = simple_function(5, 3)
        print(f"✓ Simple trace created successfully")
        print(f"  Function result: {result}")
        print(f"  Check LangSmith UI: https://smith.langchain.com/")
        return True
    except Exception as e:
        print(f"❌ Failed to create trace: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("LangSmith Integration Test")
    print("=" * 60)
    
    # Test connection
    connection_ok = test_langsmith_connection()
    
    if connection_ok:
        # Test trace creation
        trace_ok = test_simple_trace()
        
        if trace_ok:
            print("\n" + "=" * 60)
            print("✓ All tests passed!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Start FastAPI service: python -m uvicorn app.main:app --reload --port 8000")
            print("2. Test /analyze endpoint to see traces in LangSmith UI")
            print("3. Visit: https://smith.langchain.com/")
        else:
            print("\n" + "=" * 60)
            print("❌ Trace creation failed")
            print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Connection test failed")
        print("=" * 60)
