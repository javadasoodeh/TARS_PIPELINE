# WrenAI Database Query Pipeline for Open WebUI

[![Open WebUI](https://img.shields.io/badge/Open%20WebUI-Compatible-blue)](https://github.com/open-webui/open-webui)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

A powerful Open WebUI pipeline that enables natural language to SQL query conversion with automatic execution and beautiful markdown table formatting.

## 🚀 Features

- **Natural Language Processing**: Ask questions about your database in plain English
- **Automatic SQL Generation**: Converts questions to optimized SQL queries
- **Smart Execution**: Automatically runs queries and returns formatted results
- **Beautiful Formatting**: Creates markdown tables with proper number formatting
- **Error Handling**: Graceful error handling with helpful error messages
- **Configurable**: Set custom timeouts, row limits, and service URLs

## 📋 Prerequisites

- Open WebUI instance running
- Open WebUI Pipelines server running and configured
- Wren-UI service accessible
- Admin access in Open WebUI

## 🛠 Installation

### Method 1: Install from GitHub URL (Recommended)

1. **Access Open WebUI Admin Panel**:
   - Log in to your Open WebUI instance with an admin account
   - Click on the gear icon (⚙️) or your avatar in the top-right corner
   - Navigate to **Settings** → **Pipelines** tab

2. **Install from URL**:
   - Look for **"Install from URL"** or **"Add New Pipeline"** option
   - Paste this raw GitHub URL:
   ```
   https://raw.githubusercontent.com/javadasoodeh/TARS_PIPELINE/main/wrenai_pipeline.py
   ```
   - Click **Install** or **Add Pipeline**

3. **Configure Valves** (if needed):
   - Set the required environment variables:
     - `WREN_UI_URL`: URL of your Wren-UI service (default: `http://wren-ui:3000`)
     - `WREN_UI_TIMEOUT`: API timeout in seconds (default: `60`)
     - `MAX_ROWS`: Maximum rows to display (default: `500`)

4. **Activate Pipeline**:
   - Ensure the pipeline is enabled/activated
   - The pipeline should now appear in your available pipelines

### Method 2: Manual Upload

1. **Download the pipeline file**:
   ```bash
   wget https://raw.githubusercontent.com/javadasoodeh/TARS_PIPELINE/main/wrenai_pipeline.py
   ```

2. **Upload via Admin Panel**:
   - Go to **Settings** → **Pipelines**
   - Click **"Add New Pipeline"**
   - Copy and paste the content of `wrenai_pipeline.py`
   - Save and enable the pipeline

## ⚙️ Configuration

The pipeline uses these environment variables (set in Open WebUI):

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `WREN_UI_URL` | URL of your Wren-UI service | `http://wren-ui:3000` | Yes |
| `WREN_UI_TIMEOUT` | API timeout in seconds | `60` | No |
| `MAX_ROWS` | Maximum rows to display | `500` | No |

## 🎯 Usage

1. **Access Open WebUI**: Go to your Open WebUI interface
2. **Select Pipeline**: Look for "WrenAI Database Query Pipeline" in model selection
3. **Ask Questions**: Use natural language to query your database

### Example Queries

- *"What is the distribution of sales across different regions?"*
- *"Show me the top 10 customers by revenue"*
- *"Find all orders placed in the last month"*
- *"What are the average sales by product category?"*

### Sample Response

```
## 📊 Summary
The analysis shows sales distribution across different regions with detailed breakdowns.

## 🔍 SQL Query
```sql
SELECT region, SUM(sales) as total_sales
FROM sales_data
GROUP BY region
ORDER BY total_sales DESC
```

## 📋 Results (15 rows)
| Region | Total Sales |
|--------|-------------|
| North  | 1,234,567.89 |
| South  | 987,654.32  |
| East   | 876,543.21  |


## 🔧 Troubleshooting

### Pipeline Not Appearing
- Check Open WebUI logs: `docker logs open-webui`
- Verify Pipelines server is running
- Restart Open WebUI service

### Connection Issues
- Ensure Wren-UI is running and accessible
- Check `WREN_UI_URL` environment variable
- Verify network connectivity between services

### No Data Returned
- Check if database schema is indexed in Wren-UI
- Verify database connection
- Try simpler queries first

## 📞 Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Open an issue on [GitHub](https://github.com/javadasoodeh/TARS_PIPELINE/issues)
3. Contact: asoodeh.j@orchidpharmed.com

## 👨‍💻 Author

**Javad Asoodeh**  
Email: asoodeh.j@orchidpharmed.com  
GitHub: [@javadasoodeh](https://github.com/javadasoodeh)

---

⭐ **Star this repository if you find it helpful!**
