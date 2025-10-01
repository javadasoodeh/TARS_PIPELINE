#!/usr/bin/env python3
"""
Manual test script for WrenAI stream_explanation endpoint
Simple script to test individual steps manually
"""

import requests
import json
import os

def test_step_by_step():
    """Test the stream explanation flow step by step"""
    
    # Configuration
    base_url = os.getenv("WREN_UI_URL", "http://localhost:3000")
    question = "tell me about the all fields in the table"
    
    print("🧪 Manual WrenAI Stream Explanation Test")
    print("=" * 50)
    print(f"🌐 Base URL: {base_url}")
    print(f"❓ Question: {question}")
    print()
    
    headers = {
        "Accept": "application/json; charset=utf-8",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "WrenAI-Manual-Test/1.0",
    }
    
    # Step 1: Call generate_sql
    print("🔍 Step 1: Calling /api/v1/generate_sql")
    print("-" * 30)
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/generate_sql",
            json={"question": question},
            headers=headers,
            timeout=30
        )
        
        # Don't raise for status - 400 might be a valid NON_SQL_QUERY response
        data = response.json()
        print("✅ Response:")
        print(json.dumps(data, indent=2))
        
        if data.get("code") == "NON_SQL_QUERY":
            explanation_query_id = data.get("explanationQueryId")
            if explanation_query_id:
                print(f"\n🎯 Found explanationQueryId: {explanation_query_id}")
                
                # Step 2: Call stream_explanation
                print("\n🌊 Step 2: Calling /api/v1/stream_explanation")
                print("-" * 30)
                
                sse_headers = {**headers, "Accept": "text/event-stream"}
                
                response = requests.get(
                    f"{base_url}/api/v1/stream_explanation",
                    params={"queryId": explanation_query_id},
                    headers=sse_headers,
                    stream=True,
                    timeout=60
                )
                response.raise_for_status()
                
                print("✅ Stream started, receiving data...")
                print("=" * 50)
                
                full_text = ""
                message_count = 0
                
                for line in response.iter_lines(decode_unicode=True):
                    print(f"🔍 Raw line: '{line}'")  # Debug: show all lines
                    if not line:
                        continue
                    
                    if line.startswith("data:"):
                        data_str = line[len("data:"):].strip()
                        print(f"🔍 Data string: '{data_str}'")  # Debug: show data string
                        if data_str:
                            try:
                                data = json.loads(data_str)
                                print(f"🔍 Parsed JSON: {data}")  # Debug: show parsed JSON
                                
                                if data.get("done"):
                                    print("\n" + "=" * 50)
                                    print("✅ Stream completed!")
                                    print(f"📊 Messages received: {message_count}")
                                    print(f"📝 Full explanation:\n{full_text}")
                                    return True
                                
                                if "message" in data:
                                    message = data["message"]
                                    full_text += message
                                    message_count += 1
                                    print(f"📝 {message_count}: {message}", end="", flush=True)
                                    
                            except json.JSONDecodeError as e:
                                print(f"\n⚠️  JSON Error: {e}")
                                print(f"Raw data: {data_str}")
                            except Exception as e:
                                print(f"\n⚠️  Error: {e}")
                    else:
                        print(f"🔍 Non-data line: '{line}'")  # Debug: show non-data lines
                
                print(f"\n\n📝 Final text: {full_text}")
                return True
            else:
                print("❌ No explanationQueryId found in response")
                return False
        else:
            print("ℹ️  Response was not NON_SQL_QUERY")
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
    success = test_step_by_step()
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n💥 Test failed!")
