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
- Wren-UI service accessible
- Python 3.8+ (handled by Open WebUI)

## 🛠 Installation

### Method 1: Direct Upload (Recommended)

1. **Download the pipeline file**:
   ```bash
   wget https://raw.githubusercontent.com/javadasoodeh/TARS_PIPELINE/main/wrenai_pipeline.py
   ```

2. **Access Open WebUI Admin Panel**:
   - Go to `http://your-openwebui-url/admin`
   - Navigate to **Pipelines** section

3. **Upload Pipeline**:
   - Click **"Add New Pipeline"**
   - Name: `WrenAI Database Query Pipeline`
   - Copy and paste the content of `wrenai_pipeline.py`
   - Save and enable the pipeline

### Method 2: Docker Volume Mount

1. **Clone the repository**:
   ```bash
   git clone https://github.com/javadasoodeh/TARS_PIPELINE.git
   cd TARS_PIPELINE
   ```

2. **Copy to Open WebUI pipelines directory**:
   ```bash
   docker cp wrenai_pipeline.py your-openwebui-container:/app/pipelines/
   docker restart your-openwebui-container
   ```

### Method 3: Environment Variable

Add to your Open WebUI environment:
```bash
PIPELINES_URLS="https://raw.githubusercontent.com/javadasoodeh/TARS_PIPELINE/main/wrenai_pipeline.py"
```

## ⚙️ Configuration

Set these environment variables in your Open WebUI configuration:

```bash
# Required
WREN_UI_URL=http://wren-ui:3000

# Optional
WREN_UI_TIMEOUT=60          # API timeout in seconds
MAX_ROWS=500                # Maximum rows to display
```

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
```

## 🔧 Troubleshooting

### Pipeline Not Appearing
- Check Open WebUI logs: `docker logs open-webui`
- Verify pipeline file is in correct location
- Restart Open WebUI service

### Connection Issues
- Ensure Wren-UI is running and accessible
- Check `WREN_UI_URL` environment variable
- Verify network connectivity between services

### No Data Returned
- Check if database schema is indexed in Wren-UI
- Verify database connection
- Try simpler queries first

## 📁 File Structure

```
TARS_PIPELINE/
├── wrenai_pipeline.py      # Main pipeline implementation
├── requirements.txt        # Python dependencies
├── pipeline_config.py      # Configuration management
└── README.md              # This file
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Javad Asoodeh**
- Email: asoodeh.j@orchidpharmed.com
- GitHub: [@javadasoodeh](https://github.com/javadasoodeh)

## 🙏 Acknowledgments

- [Open WebUI](https://github.com/open-webui/open-webui) for the amazing platform
- [Wren-UI](https://github.com/Canner/wren-ui) for the SQL generation capabilities

## 📞 Support

If you encounter any issues or have questions:

1. Check the [troubleshooting section](#-troubleshooting)
2. Open an issue on [GitHub](https://github.com/javadasoodeh/TARS_PIPELINE/issues)
3. Contact: asoodeh.j@orchidpharmed.com

---

⭐ **Star this repository if you find it helpful!**
