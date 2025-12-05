"""
Test script for conversational AI agent.

Run this to test the chat functionality.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/ai/chat"


def test_conversation():
    """Test a complete conversation flow."""
    
    print("=" * 60)
    print("Testing Conversational AI Agent")
    print("=" * 60)
    
    # 1. Start conversation
    print("\n1. Starting conversation...")
    response = requests.post(f"{BASE_URL}/start", json={})
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]
    print(f"✓ Session started: {session_id}")
    print(f"  Bot: {data['message']}")
    
    # 2. Send first message (vague query)
    print("\n2. Sending vague query...")
    response = requests.post(f"{BASE_URL}/message", json={
        "session_id": session_id,
        "message": "I need developers"
    })
    assert response.status_code == 200
    data = response.json()
    print(f"  User: I need developers")
    print(f"  Bot: {data['message']}")
    print(f"  Intent: {data['intent']} (confidence: {data['confidence']:.2f})")
    if data['needs_clarification']:
        print(f"  Clarifying questions: {data['clarifying_questions']}")
    
    # 3. Send more specific query
    print("\n3. Sending specific query...")
    response = requests.post(f"{BASE_URL}/message", json={
        "session_id": session_id,
        "message": "I'm looking for a senior Python developer with Django experience"
    })
    assert response.status_code == 200
    data = response.json()
    print(f"  User: I'm looking for a senior Python developer with Django experience")
    print(f"  Bot: {data['message']}")
    print(f"  Intent: {data['intent']} (confidence: {data['confidence']:.2f})")
    print(f"  Extracted context: {json.dumps(data['context'], indent=2)}")
    
    # 4. Ask about a candidate
    print("\n4. Asking about a candidate...")
    response = requests.post(f"{BASE_URL}/message", json={
        "session_id": session_id,
        "message": "Tell me more about the first candidate"
    })
    assert response.status_code == 200
    data = response.json()
    print(f"  User: Tell me more about the first candidate")
    print(f"  Bot: {data['message']}")
    print(f"  Intent: {data['intent']} (confidence: {data['confidence']:.2f})")
    
    # 5. Get conversation history
    print("\n5. Getting conversation history...")
    response = requests.get(f"{BASE_URL}/history/{session_id}")
    assert response.status_code == 200
    data = response.json()
    print(f"✓ Retrieved {data['message_count']} messages")
    print(f"  Started: {data['started_at']}")
    print(f"  Last message: {data['last_message_at']}")
    
    # 6. End conversation
    print("\n6. Ending conversation...")
    response = requests.delete(f"{BASE_URL}/{session_id}")
    assert response.status_code == 200
    print(f"✓ Conversation ended")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_conversation()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to FastAPI server")
        print("   Make sure the server is running on http://localhost:8000")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
