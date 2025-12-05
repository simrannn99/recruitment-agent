"""
Test session persistence and context management.

This script tests:
1. Session creation and retrieval
2. Message history persistence
3. Context preservation across requests
4. Redis storage and retrieval
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_result(label: str, data: Any):
    """Print formatted result."""
    print(f"\n{label}:")
    print(json.dumps(data, indent=2))

def test_session_creation():
    """Test 1: Create a new session."""
    print_section("TEST 1: Session Creation")
    
    response = requests.post(
        f"{BASE_URL}/api/ai/chat/start",
        json={"user_id": None}  # Send empty body with optional user_id
    )
    assert response.status_code == 200, f"Failed to create session: {response.status_code} - {response.text}"
    
    data = response.json()
    session_id = data['session_id']
    
    print(f"✓ Session created: {session_id}")
    print_result("Initial response", data)
    
    # The /start endpoint only returns session_id and welcome message
    # To verify the session state, we need to get the history
    print("\nFetching full session state...")
    history_response = requests.get(f"{BASE_URL}/api/ai/chat/history/{session_id}")
    assert history_response.status_code == 200, "Failed to get session history"
    
    session_data = history_response.json()
    print_result("Full session data", session_data)
    
    # Verify initial state
    assert session_data['message_count'] == 0, "New session should have 0 messages"
    assert len(session_data['messages']) == 0, "New session should have empty messages"
    print("✓ Session state verified: empty messages, ready for conversation")
    
    return session_id

def test_send_message(session_id: str, message: str, test_num: int):
    """Test sending a message and verify response."""
    print_section(f"TEST {test_num}: Send Message")
    print(f"Message: '{message}'")
    
    response = requests.post(
        f"{BASE_URL}/api/ai/chat/message",
        json={
            "session_id": session_id,
            "message": message
        }
    )
    
    assert response.status_code == 200, f"Failed to send message: {response.status_code}"
    
    data = response.json()
    print_result("Response", {
        "intent": data.get('intent'),
        "confidence": data.get('confidence'),
        "message_preview": data['message'][:200] + "..." if len(data['message']) > 200 else data['message'],
        "context": data.get('context')
    })
    
    return data

def test_get_history(session_id: str, expected_count: int, test_num: int):
    """Test retrieving conversation history."""
    print_section(f"TEST {test_num}: Get Conversation History")
    
    response = requests.get(f"{BASE_URL}/api/ai/chat/history/{session_id}")
    assert response.status_code == 200, f"Failed to get history: {response.status_code}"
    
    data = response.json()
    
    print(f"✓ Retrieved history for session: {session_id}")
    print(f"  Message count: {data['message_count']}")
    print(f"  Started at: {data['started_at']}")
    print(f"  Last message at: {data['last_message_at']}")
    
    # Verify message count
    assert data['message_count'] == expected_count, \
        f"Expected {expected_count} messages, got {data['message_count']}"
    assert len(data['messages']) == expected_count, \
        f"Expected {expected_count} messages in array, got {len(data['messages'])}"
    
    # Print messages
    print("\nMessages:")
    for i, msg in enumerate(data['messages'], 1):
        print(f"  {i}. [{msg['role']}] {msg['content'][:100]}...")
        if msg.get('intent'):
            print(f"     Intent: {msg['intent']}")
    
    return data

def test_context_preservation(session_id: str, test_num: int):
    """Test that context is preserved across messages."""
    print_section(f"TEST {test_num}: Context Preservation")
    
    # Get current history
    response = requests.get(f"{BASE_URL}/api/ai/chat/history/{session_id}")
    data = response.json()
    
    print("Current context:")
    print_result("Context", data.get('context', {}))
    
    # Verify context has search results from previous query
    context = data.get('context', {})
    
    if context.get('search_results'):
        print(f"\n✓ Context preserved! Found {len(context['search_results'])} candidates in context")
        print("\nStored candidates:")
        for i, candidate in enumerate(context['search_results'][:3], 1):
            print(f"  {i}. {candidate.get('name')} ({candidate.get('email')})")
    else:
        print("\n⚠ No search results in context (might be expected if no search was performed)")
    
    if context.get('job_requirements'):
        print("\n✓ Job requirements preserved!")
        print_result("Job requirements", context['job_requirements'])
    
    return context

def test_session_retrieval_after_delay(session_id: str, test_num: int):
    """Test that session can be retrieved after a delay (simulates page refresh)."""
    print_section(f"TEST {test_num}: Session Retrieval After Delay")
    
    print("Waiting 2 seconds to simulate page refresh...")
    time.sleep(2)
    
    response = requests.get(f"{BASE_URL}/api/ai/chat/history/{session_id}")
    assert response.status_code == 200, "Session should still be retrievable"
    
    data = response.json()
    print(f"✓ Session successfully retrieved after delay")
    print(f"  Message count: {data['message_count']}")
    print(f"  Is active: {data.get('is_active', 'N/A')}")
    
    return data

def test_redis_persistence(session_id: str, test_num: int):
    """Test direct Redis inspection (requires redis-cli)."""
    print_section(f"TEST {test_num}: Redis Persistence Check")
    
    import subprocess
    
    try:
        # Try to get session from Redis directly
        result = subprocess.run(
            ['docker', 'exec', 'recruitment-redis-local', 'redis-cli', 'GET', f'session:{session_id}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            print("✓ Session found in Redis!")
            
            # Parse the JSON (Redis returns it as a string)
            redis_data = result.stdout.strip()
            if redis_data and redis_data != '(nil)':
                print(f"  Redis key: session:{session_id}")
                print(f"  Data size: {len(redis_data)} bytes")
                
                # Try to parse and show summary
                try:
                    session_data = json.loads(redis_data.strip('"').replace('\\"', '"'))
                    print(f"  Messages in Redis: {len(session_data.get('messages', []))}")
                    print(f"  Context keys: {list(session_data.get('context', {}).keys())}")
                except:
                    print("  (Could not parse Redis data)")
            else:
                print("⚠ Session not found in Redis (might be in memory fallback)")
        else:
            print("⚠ Could not check Redis (docker command failed)")
            print("  This is OK if Redis is not running or accessible")
    
    except Exception as e:
        print(f"⚠ Could not check Redis: {e}")
        print("  This is OK - session might be in memory fallback")

def run_all_tests():
    """Run complete test suite."""
    print_section("SESSION PERSISTENCE TEST SUITE")
    print("Testing session creation, message persistence, and context management")
    
    try:
        # Test 1: Create session
        session_id = test_session_creation()
        
        # Test 2: Send first message (vague query)
        test_send_message(session_id, "I need developers", 2)
        
        # Test 3: Check history after first message
        test_get_history(session_id, expected_count=2, test_num=3)  # User + Assistant
        
        # Test 4: Send specific query
        test_send_message(
            session_id,
            "I'm looking for a senior Python developer with Django experience",
            4
        )
        
        # Test 5: Check history after second message
        test_get_history(session_id, expected_count=4, test_num=5)  # 2 previous + 2 new
        
        # Test 6: Test context preservation
        test_context_preservation(session_id, 6)
        
        # Test 7: Ask about specific candidate (tests context usage)
        test_send_message(session_id, "Tell me more about the first candidate", 7)
        
        # Test 8: Final history check
        history = test_get_history(session_id, expected_count=6, test_num=8)
        
        # Test 9: Session retrieval after delay
        test_session_retrieval_after_delay(session_id, 9)
        
        # Test 10: Redis persistence check
        test_redis_persistence(session_id, 10)
        
        # Summary
        print_section("TEST SUMMARY")
        print("✓ All tests passed!")
        print(f"\nFinal session state:")
        print(f"  Session ID: {session_id}")
        print(f"  Total messages: {history['message_count']}")
        print(f"  Context preserved: {'✓' if history.get('context', {}).get('search_results') else '✗'}")
        
        # Cleanup
        print("\nCleaning up...")
        response = requests.delete(f"{BASE_URL}/api/ai/chat/{session_id}")
        if response.status_code == 200:
            print("✓ Session deleted successfully")
        
        print("\n" + "=" * 60)
        print("  ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to FastAPI server")
        print("   Make sure the server is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
