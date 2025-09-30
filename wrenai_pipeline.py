"""
title: WrenAI Database Query Pipeline
author: Javad Asoodeh
date: 2025-01-30
version: 1.0
license: MIT
description: A pipeline for natural language to SQL query conversion using Wren-UI APIs with automatic execution and markdown table formatting.
requirements: requests, pydantic
"""

import requests
import logging
from typing import List, Union, Generator, Iterator
import os
from pydantic import BaseModel
import json

logging.basicConfig(level=logging.INFO)

class Pipeline:
    class Valves(BaseModel):
        WREN_UI_URL: str
        WREN_UI_TIMEOUT: int
        MAX_ROWS: int
        MODEL_NAME: str

    def __init__(self):
        self.nlsql_response = ""

        self.valves = self.Valves(
            **{
                "pipelines": ["*"],
                "WREN_UI_URL": os.getenv("WREN_UI_URL", "http://wren-ui:3000"),
                "WREN_UI_TIMEOUT": int(os.getenv("WREN_UI_TIMEOUT", "60")),
                "MAX_ROWS": int(os.getenv("MAX_ROWS", "500")),
                "MODEL_NAME": os.getenv("MODEL_NAME", "WrenAI Database Query Pipeline"),
            }
        )
        
        # Set the name from the valve value
        self.name = self.valves.MODEL_NAME

    @property
    def name(self):
        """Dynamic name property that updates when valves change."""
        return self.valves.MODEL_NAME

    @name.setter
    def name(self, value):
        """Setter for name property."""
        self._name = value

    async def on_startup(self):
        """Initialize the pipeline on startup."""
        # Update name in case valves were changed after initialization
        self.name = self.valves.MODEL_NAME
        logging.info(f"WrenAI Pipeline started with URL: {self.valves.WREN_UI_URL}")
        logging.info(f"Pipeline name: {self.name}")

    async def on_shutdown(self):
        """Cleanup on shutdown."""
        logging.info("WrenAI Pipeline shutdown")

    def make_request_with_retry(self, url: str, method: str = "POST", data: dict = None, retries: int = 3, timeout: int = 60):
        """Make HTTP request with retry logic."""
        headers = {
            "Accept": "application/json; charset=utf-8",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "WrenAI-Pipeline/1.0"
        }
        
        for attempt in range(retries):
            try:
                if method.upper() == "POST":
                    response = requests.post(url, json=data, headers=headers, timeout=timeout)
                else:
                    response = requests.get(url, headers=headers, timeout=timeout)
                
                # Handle 400 responses that contain JSON error messages
                if response.status_code == 400:
                    try:
                        error_data = response.json()
                        logging.warning(f"400 Bad Request: {error_data}")
                        return error_data  # Return the error data instead of raising
                    except:
                        response.raise_for_status()
                else:
                    response.raise_for_status()
                
                return response.json()
                
            except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                logging.error(f"Attempt {attempt + 1} failed with error: {e}")
                if attempt + 1 == retries:
                    raise
                import time
                time.sleep(2 ** attempt)  # Exponential backoff

    def create_markdown_table(self, records: List[dict], columns: List[dict], max_rows: int = 500) -> str:
        """Create a markdown table from SQL query results."""
        if not records or not columns:
            return "No data available."
        
        # Limit rows to max_rows
        limited_records = records[:max_rows]
        
        # Get column names
        column_names = [col["name"] for col in columns]
        
        # Create table header
        header = "| " + " | ".join(column_names) + " |"
        separator = "| " + " | ".join(["---"] * len(column_names)) + " |"
        
        # Create table rows
        rows = []
        for record in limited_records:
            row_values = []
            for col_name in column_names:
                value = record.get(col_name, "")
                # Format the value for better readability
                if isinstance(value, (int, float)):
                    if isinstance(value, float):
                        # Format large numbers with commas
                        if abs(value) >= 1000:
                            formatted_value = f"{value:,.2f}"
                        else:
                            formatted_value = f"{value:.2f}"
                    else:
                        formatted_value = f"{value:,}"
                else:
                    formatted_value = str(value) if value is not None else ""
                
                row_values.append(formatted_value)
            
            row = "| " + " | ".join(row_values) + " |"
            rows.append(row)
        
        # Combine header, separator, and rows
        table_lines = [header, separator] + rows
        
        # Add summary
        total_rows = len(records)
        displayed_rows = len(limited_records)
        
        summary = f"\n**Total rows:** {total_rows:,}"
        if displayed_rows < total_rows:
            summary += f" (showing first {displayed_rows:,} rows)"
        
        return "\n".join(table_lines) + summary

    def clean_text(self, text: str) -> str:
        """Convert API response text to proper markdown format for Open WebUI rendering."""
        if not text:
            return text
        
        # Replace escaped newlines with actual newlines
        cleaned = text.replace('\\n', '\n')
        
        # Replace escaped quotes
        cleaned = cleaned.replace('\\"', '"')
        cleaned = cleaned.replace("\\'", "'")
        
        # Replace escaped backslashes
        cleaned = cleaned.replace('\\\\', '\\')
        
        # Convert to proper markdown format
        lines = cleaned.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                formatted_lines.append('')
                continue
                
            # Handle numbered lists (1. Item, 2. Item, etc.)
            if line[0].isdigit() and '. ' in line:
                # Ensure proper markdown list formatting
                formatted_lines.append(line)
            # Handle bullet points or other list items
            elif line.startswith('- ') or line.startswith('* '):
                formatted_lines.append(line)
            # Handle headers (if any)
            elif line.startswith('#'):
                formatted_lines.append(line)
            # Handle regular paragraphs
            else:
                # Add proper spacing for paragraphs
                if formatted_lines and formatted_lines[-1] and not formatted_lines[-1].startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '-', '*', '#')):
                    # Add a blank line before new paragraphs
                    if not formatted_lines[-1].startswith('\n'):
                        formatted_lines.append('')
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)

    def ask_question(self, question: str, thread_id: str = None) -> dict:
        """Ask a question to Wren-UI API."""
        ask_url = f"{self.valves.WREN_UI_URL}/api/v1/ask"
        
        payload = {
            "question": question
        }
        
        # Add thread ID for follow-up questions
        if thread_id:
            payload["threadId"] = thread_id

        logging.info(f"Asking question: {question}")
        
        try:
            response = self.make_request_with_retry(
                ask_url, 
                method="POST", 
                data=payload, 
                timeout=self.valves.WREN_UI_TIMEOUT
            )
            
            # Check if the response contains an error
            if response.get("error") or response.get("code") == "NO_RELEVANT_DATA":
                logging.warning(f"Wren-UI returned error: {response.get('error', 'Unknown error')}")
                return response  # Return the error response as-is
            
            logging.info(f"Ask response received: {response.get('id', 'unknown')}")
            return response
        except Exception as e:
            logging.error(f"Error asking question: {e}")
            return {
                "id": "error",
                "error": f"Failed to ask question: {str(e)}"
            }

    def run_sql(self, sql: str, thread_id: str = None) -> dict:
        """Execute SQL query using Wren-UI API."""
        run_sql_url = f"{self.valves.WREN_UI_URL}/api/v1/run_sql"
        
        payload = {
            "sql": sql
        }
        if thread_id:
            payload["threadId"] = thread_id

        logging.info(f"Running SQL: {sql[:100]}...")
        
        try:
            response = self.make_request_with_retry(
                run_sql_url, 
                method="POST", 
                data=payload, 
                timeout=self.valves.WREN_UI_TIMEOUT
            )
            logging.info(f"SQL execution successful, got {len(response.get('records', []))} records")
            return response
        except Exception as e:
            logging.error(f"Error executing SQL: {e}")
            return {
                "error": f"Failed to execute SQL: {str(e)}",
                "records": [],
                "columns": [],
                "totalRows": 0
            }

    def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> Union[str, Generator, Iterator]:
        """Main pipeline function that processes user queries."""
        try:
            # Extract thread ID from Open WebUI context for follow-up questions
            thread_id = None
            if body and 'metadata' in body:
                metadata = body['metadata']
                # Try to get thread ID from various possible locations
                thread_id = metadata.get('chat_id') or metadata.get('session_id') or metadata.get('thread_id')
                if thread_id:
                    logging.info(f"Using thread ID for follow-up question: {thread_id}")
                else:
                    logging.info("No thread ID found in metadata, treating as new conversation")
            else:
                logging.info("No metadata found in body, treating as new conversation")
            
            # Step 1: Ask the question to get SQL query and summary
            logging.info("Step 1: Asking question to Wren-UI...")
            ask_response = self.ask_question(user_message, thread_id)
            
            # Check for errors in the response
            if ask_response.get("error") or ask_response.get("code") == "NO_RELEVANT_DATA":
                error_msg = self.clean_text(ask_response.get("error", "Unknown error occurred"))
                yield f"## ❌ Database Query Error\n\n**Error:** {error_msg}\n\n*This usually means the database schema hasn't been indexed yet or the question doesn't match available data. Please try a different question or check if the database is properly set up.*"
                return
            
            # Stream response content
            # Add summary if available
            if ask_response.get("summary"):
                # Clean up the summary text formatting
                clean_summary = self.clean_text(ask_response['summary'])
                yield f"## 📊 Summary\n\n{clean_summary}\n\n"
            
            # Add SQL query if present
            if ask_response.get("sql"):
                yield f"## 🔍 SQL Query\n\n```sql\n{ask_response['sql']}\n```\n\n"
                
                # Step 2: Execute the SQL query
                logging.info("Step 2: Executing SQL query...")
                sql_response = self.run_sql(ask_response["sql"], ask_response.get("threadId") or thread_id)
                
                if sql_response.get("error"):
                    yield f"## ❌ SQL Execution Error\n\n{sql_response['error']}"
                else:
                    records = sql_response.get("records", [])
                    columns = sql_response.get("columns", [])
                    total_rows = sql_response.get("totalRows", 0)
                    
                    if records and columns:
                        yield f"## 📋 Results ({total_rows:,} rows)\n\n"
                        # Create the table and stream it in small chunks to avoid "Chunk too big" error
                        table_content = self.create_markdown_table(records, columns, self.valves.MAX_ROWS)
                        # Split table into smaller chunks for streaming
                        chunk_size = 2000  # Smaller chunks to prevent "Chunk too big" error
                        for i in range(0, len(table_content), chunk_size):
                            yield table_content[i:i + chunk_size]
                    else:
                        yield "## 📋 Results\n\n*No data returned from the query.*"
            else:
                yield "## ⚠️ No SQL Query Generated\n\n*The question could not be converted to a SQL query.*"
            
            logging.info("Pipeline completed successfully")
            
        except Exception as e:
            logging.error(f"Pipeline execution error: {e}")
            yield f"**Pipeline Error:** {str(e)}"
