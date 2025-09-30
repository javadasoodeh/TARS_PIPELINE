"""
Configuration file for WrenAI Pipeline
"""
import os

# Pipeline configuration
PIPELINE_CONFIG = {
    "name": "WrenAI Database Query Pipeline",
    "description": "A pipeline that uses Wren-UI APIs to generate SQL queries and execute them against the database",
    "version": "1.0.0",
    "author": "Javad Asoodeh",
    "email": "asoodeh.j@orchidpharmed.com",
    "requirements": [
        "requests>=2.31.0",
        "pydantic>=2.0.0"
    ],
    "environment_variables": {
        "WREN_UI_URL": {
            "description": "URL of the Wren-UI service",
            "default": "http://wren-ui:3000",
            "required": True
        },
        "WREN_UI_TIMEOUT": {
            "description": "Timeout for API requests in seconds",
            "default": "60",
            "required": False
        },
        "MAX_ROWS": {
            "description": "Maximum number of rows to display in tables",
            "default": "500",
            "required": False
        }
    },
    "features": [
        "Natural language to SQL conversion",
        "SQL query execution",
        "Markdown table formatting",
        "Error handling and retry logic",
        "Configurable row limits",
        "Summary generation"
    ]
}

def get_config():
    """Get the pipeline configuration."""
    return PIPELINE_CONFIG

def validate_environment():
    """Validate that required environment variables are set."""
    required_vars = ["WREN_UI_URL"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True
