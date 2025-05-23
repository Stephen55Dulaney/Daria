#!/usr/bin/env python
"""
Script to check if the DARIA server is running correctly and LangChain is working.
This performs a series of API calls to verify functionality.
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:5025"

def print_status(message, success=True):
    """Print a status message with appropriate coloring."""
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")

def check_health():
    """Check the health endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        data = response.json()
        if response.status_code == 200 and data.get("status") == "ok":
            print_status("Health check passed")
            return True
        else:
            print_status(f"Health check failed: {data}", success=False)
            return False
    except Exception as e:
        print_status(f"Health check error: {str(e)}", success=False)
        return False

def create_session():
    """Create a new session and return the session ID."""
    try:
        # First get a guide ID
        response = requests.get(f"{BASE_URL}/api/discussion_guides")
        if response.status_code != 200:
            print_status("Failed to get discussion guides", success=False)
            return None
        
        guides = response.json()
        if not guides:
            print_status("No discussion guides found", success=False)
            return None
            
        guide_id = guides[0].get("id")
        
        # Create a session
        response = requests.post(
            f"{BASE_URL}/api/session",
            json={"discussion_guide_id": guide_id}
        )
        
        if response.status_code == 200:
            session_id = response.json().get("session_id")
            print_status(f"Session created with ID: {session_id}")
            return session_id
        else:
            print_status(f"Failed to create session: {response.status_code}", success=False)
            return None
    except Exception as e:
        print_status(f"Session creation error: {str(e)}", success=False)
        return None

def test_messages(session_id):
    """Test sending and receiving messages."""
    if not session_id:
        return False
        
    try:
        # Send a message
        response = requests.post(
            f"{BASE_URL}/api/session/{session_id}/add_message",
            json={
                "message": "Hello, this is a test message",
                "role": "user"
            }
        )
        
        if response.status_code != 200:
            print_status(f"Failed to send message: {response.status_code}", success=False)
            return False
            
        message_id = response.json().get("message_id")
        print_status(f"Message sent successfully with ID: {message_id}")
        
        # Wait for the message to be processed
        time.sleep(2)
        
        # Get messages
        response = requests.get(f"{BASE_URL}/api/session/{session_id}/messages")
        
        if response.status_code != 200:
            print_status(f"Failed to fetch messages: {response.status_code}", success=False)
            return False
            
        messages = response.json()
        if not messages:
            print_status("No messages returned", success=False)
            return False
            
        print_status(f"Retrieved {len(messages)} messages")
        return True
    except Exception as e:
        print_status(f"Message testing error: {str(e)}", success=False)
        return False

def test_langchain_endpoints():
    """Test LangChain-specific endpoints."""
    try:
        # Check characters endpoint
        response = requests.get(f"{BASE_URL}/api/characters")
        
        if response.status_code == 200:
            characters = response.json()
            if characters:
                print_status(f"Successfully retrieved {len(characters)} characters")
                return True
            else:
                print_status("Characters endpoint returned empty list", success=False)
                return False
        else:
            # Try prompts endpoint as fallback
            response = requests.get(f"{BASE_URL}/api/prompts")
            if response.status_code == 200:
                print_status("Successfully retrieved prompts")
                return True
            else:
                print_status(f"Failed to access LangChain endpoints: {response.status_code}", success=False)
                return False
    except Exception as e:
        print_status(f"LangChain endpoint error: {str(e)}", success=False)
        return False

def main():
    """Main function to run all tests."""
    print("DARIA Server Check")
    print("=" * 40)
    
    # Check if server is running
    if not check_health():
        print("\nServer health check failed. Make sure the server is running.")
        sys.exit(1)
    
    # Check LangChain endpoints
    langchain_working = test_langchain_endpoints()
    
    # Create a session and test messages
    session_id = create_session()
    messages_working = test_messages(session_id)
    
    # Summary
    print("\nTest Summary:")
    print(f"Health Check: {'✅' if True else '❌'}")
    print(f"LangChain Endpoints: {'✅' if langchain_working else '❌'}")
    print(f"Session Creation: {'✅' if session_id else '❌'}")
    print(f"Message Handling: {'✅' if messages_working else '❌'}")
    
    if not langchain_working or not session_id or not messages_working:
        print("\nSome tests failed. Check the DARIA server logs for more information.")
        sys.exit(1)
    else:
        print("\nAll tests passed! DARIA server is working correctly.")
        sys.exit(0)

if __name__ == "__main__":
    main() 