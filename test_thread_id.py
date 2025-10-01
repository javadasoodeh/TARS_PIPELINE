import requests
import json
import os

def test_thread_id_capture():
    """Test thread ID capture from streaming responses"""
    
    # Configuration
    base_url = os.getenv("WREN_UI_URL", "http://localhost:3000")
    question = "show me the data"
    
    headers = {
        "Accept": "application/json; charset=utf-8",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "WrenAI-Test-Client/1.0",
        "Connection": "keep-alive",
    }

    print("🧪 Thread ID Capture Test")
    print("=" * 50)
    print(f"🌐 Base URL: {base_url}")
    print(f"❓ Question: {question}")
    print("\n" + "=" * 50)

    try:
        # Test streaming generate_sql
        print("🔍 Testing /api/v1/stream/generate_sql")
        print("-" * 30)
        
        sse_headers = {**headers, "Accept": "text/event-stream"}
        
        response = requests.post(
            f"{base_url}/api/v1/stream/generate_sql",
            json={"question": question},
            headers=sse_headers,
            stream=True,
            timeout=60
        )
        response.raise_for_status()
        
        print("✅ Stream started, looking for thread ID...")
        print("=" * 50)
        
        thread_id_found = False
        message_count = 0
        
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            
            if line.startswith("data:"):
                data_str = line[len("data:"):].strip()
                if data_str:
                    try:
                        data = json.loads(data_str)
                        message_count += 1
                        
                        # Check for thread ID in different places
                        if data.get("type") == "state":
                            state_data = data.get("data", {})
                            if state_data.get("state") == "sql_generation_start" and state_data.get("threadId"):
                                print(f"✅ Found thread ID in sql_generation_start: {state_data['threadId']}")
                                thread_id_found = True
                            elif state_data.get("threadId"):
                                print(f"✅ Found thread ID in state data: {state_data['threadId']}")
                                thread_id_found = True
                        
                        elif data.get("type") == "message_stop":
                            stop_data = data.get("data", {})
                            if stop_data.get("threadId"):
                                print(f"✅ Found thread ID in message_stop: {stop_data['threadId']}")
                                thread_id_found = True
                        
                        # Show the event for debugging
                        if message_count <= 5:  # Show first 5 events
                            print(f"📝 Event {message_count}: {data.get('type', 'unknown')}")
                            if data.get("data", {}).get("state"):
                                print(f"   State: {data['data']['state']}")
                            if data.get("data", {}).get("threadId"):
                                print(f"   Thread ID: {data['data']['threadId']}")
                        
                        if data.get("type") == "message_stop":
                            print(f"\n📊 Total events processed: {message_count}")
                            break
                            
                    except json.JSONDecodeError as e:
                        print(f"⚠️  JSON Error: {e}")
                    except Exception as e:
                        print(f"⚠️  Error: {e}")
        
        if thread_id_found:
            print("\n🎉 Thread ID capture test PASSED!")
            return True
        else:
            print("\n❌ Thread ID capture test FAILED - no thread ID found")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_thread_id_capture()
