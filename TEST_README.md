# WrenAI Stream Explanation Test Suite

This directory contains test scripts to verify that the WrenAI stream explanation functionality works correctly.

## Test Files

### 1. `test_stream_explanation.py` - Comprehensive Test Suite
- Tests multiple questions that should trigger NON_SQL_QUERY responses
- Automatically tests the complete flow: `generate_sql` → `stream_explanation`
- Provides detailed output and statistics
- Tests error handling and edge cases

**Usage:**
```bash
# Set the Wren-UI URL (optional, defaults to http://wren-ui:3000)
export WREN_UI_URL=http://your-wren-ui-host:3000

# Run the comprehensive test suite
python test_stream_explanation.py
```

### 2. `manual_test_explanation.py` - Simple Manual Test
- Tests a single question step by step
- Shows detailed output for each step
- Good for debugging and understanding the flow
- Easier to modify for specific test cases

**Usage:**
```bash
# Set the Wren-UI URL (optional, defaults to http://wren-ui:3000)
export WREN_UI_URL=http://your-wren-ui-host:3000

# Run the manual test
python manual_test_explanation.py
```

## Test Flow

Both test scripts follow this flow:

1. **Call `/api/v1/generate_sql`** with a general question
2. **Check for NON_SQL_QUERY response** and extract `explanationQueryId`
3. **Call `/api/v1/stream_explanation`** with the `explanationQueryId`
4. **Parse Server-Sent Events (SSE)** stream and collect explanation text
5. **Verify completion** with `{"done":true}` marker

## Expected Output

The stream explanation should return data in this format:

```
data: {"message":"Wren AI is "}
data: {"message":"designed to "}
data: {"message":"help you analyze "}
data: {"message":"your data with "}
data: {"message":"natural language queries. I can "}
data: {"message":"provide insights about "}
data: {"message":"your business data and "}
data: {"message":"create visualizations."}
data: {"done":true}
```

## Troubleshooting

### Common Issues:

1. **Connection Refused**: Make sure Wren-UI is running and accessible
2. **No explanationQueryId**: The question might not trigger NON_SQL_QUERY
3. **Stream Timeout**: The explanation might take longer than expected
4. **JSON Parse Errors**: The stream format might be different than expected

### Debug Tips:

- Use `manual_test_explanation.py` for step-by-step debugging
- Check the raw response from `generate_sql` first
- Verify the `explanationQueryId` is valid
- Test with different questions that should trigger explanations

## Environment Variables

- `WREN_UI_URL`: Base URL for Wren-UI service (default: `http://wren-ui:3000`)

## Requirements

- Python 3.6+
- requests library
- Access to Wren-UI service
