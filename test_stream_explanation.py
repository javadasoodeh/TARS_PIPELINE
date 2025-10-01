#!/usr/bin/env python3
"""
Test script for WrenAI stream_explanation endpoint
Tests the complete flow: generate_sql -> get explanationQueryId -> stream_explanation
"""

import requests
import json
import time
import os
from typing import Optional

class WrenAITester:
    def __init__(self, base_url: str = "http://wren-ui:3000"):
        self.base_url = base_url
        self.headers = {
            "Accept": "application/json; charset=utf-8",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "WrenAI-Test-Script/1.0",
            "Connection": "keep-alive",
        }

    def test_generate_sql(self, question: str) -> Optional[str]:
        """Test the generate_sql endpoint and return explanationQueryId if NON_SQL_QUERY"""
        print(f"🔍 Testing generate_sql with question: '{question}'")
        
        url = f"{self.base_url}/api/v1/generate_sql"
        payload = {"question": question}
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Response received: {json.dumps(data, indent=2)}")
            
            if data.get("code") == "NON_SQL_QUERY":
                explanation_query_id = data.get("explanationQueryId")
                if explanation_query_id:
                    print(f"🎯 Found explanationQueryId: {explanation_query_id}")
                    return explanation_query_id
                else:
                    print("❌ NON_SQL_QUERY response but no explanationQueryId found")
                    return None
            else:
                print("ℹ️  Response was not NON_SQL_QUERY, no explanation needed")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error calling generate_sql: {e}")
            return None

    def test_stream_explanation(self, explanation_query_id: str) -> bool:
        """Test the stream_explanation endpoint"""
        print(f"🌊 Testing stream_explanation with ID: {explanation_query_id}")
        
        url = f"{self.base_url}/api/v1/stream_explanation"
        params = {"explanationQueryId": explanation_query_id}
        
        # Update headers for SSE
        sse_headers = {**self.headers, "Accept": "text/event-stream"}
        
        try:
            response = requests.get(url, params=params, headers=sse_headers, stream=True, timeout=60)
            response.raise_for_status()
            
            print("📡 Starting to receive stream...")
            print("=" * 50)
            
            full_explanation = ""
            message_count = 0
            
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                    
                # Parse SSE format: "data: {...json...}"
                if line.startswith("data:"):
                    data_str = line[len("data:"):].strip()
                    if data_str:
                        try:
                            data = json.loads(data_str)
                            
                            # Check if stream is done
                            if data.get("done"):
                                print("\n" + "=" * 50)
                                print("✅ Stream completed!")
                                print(f"📊 Total messages received: {message_count}")
                                print(f"📝 Full explanation length: {len(full_explanation)} characters")
                                return True
                            
                            # Handle message chunks
                            if "message" in data:
                                message = data["message"]
                                full_explanation += message
                                message_count += 1
                                print(f"📝 Message {message_count}: '{message}'")
                                
                        except json.JSONDecodeError as e:
                            print(f"⚠️  Failed to parse JSON: {data_str} - Error: {e}")
                        except Exception as e:
                            print(f"⚠️  Unexpected error processing line: {e}")
            
            print("\n" + "=" * 50)
            print("✅ Stream completed (no 'done' marker received)")
            print(f"📊 Total messages received: {message_count}")
            print(f"📝 Full explanation: {full_explanation}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error calling stream_explanation: {e}")
            return False

    def test_complete_flow(self, question: str) -> bool:
        """Test the complete flow: generate_sql -> stream_explanation"""
        print("🚀 Starting complete WrenAI explanation flow test")
        print("=" * 60)
        
        # Step 1: Get explanationQueryId
        explanation_query_id = self.test_generate_sql(question)
        if not explanation_query_id:
            print("❌ Failed to get explanationQueryId, cannot test stream_explanation")
            return False
        
        print("\n" + "=" * 60)
        
        # Step 2: Stream explanation
        success = self.test_stream_explanation(explanation_query_id)
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 Complete flow test PASSED!")
        else:
            print("💥 Complete flow test FAILED!")
        
        return success

def main():
    """Main test function"""
    print("🧪 WrenAI Stream Explanation Test Suite")
    print("=" * 60)
    
    # Get base URL from environment or use default
    base_url = os.getenv("WREN_UI_URL", "http://wren-ui:3000")
    print(f"🌐 Using Wren-UI URL: {base_url}")
    
    # Initialize tester
    tester = WrenAITester(base_url)
    
    # Test questions that should trigger NON_SQL_QUERY
    test_questions = [
        "Can you explain what the data in the amarnameh_MOH_MarketData_1403 table is about?",
        "What is this database about?",
        "Hello, how are you?",
        "What can you help me with?",
        "Tell me about the data structure"
    ]
    
    print(f"\n📋 Testing {len(test_questions)} questions...")
    
    success_count = 0
    total_tests = len(test_questions)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n🔬 Test {i}/{total_tests}")
        print("-" * 40)
        
        if tester.test_complete_flow(question):
            success_count += 1
        
        # Add delay between tests
        if i < total_tests:
            print("\n⏳ Waiting 2 seconds before next test...")
            time.sleep(2)
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All tests PASSED! Stream explanation is working correctly.")
        return 0
    else:
        print("💥 Some tests FAILED! Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit(main())
