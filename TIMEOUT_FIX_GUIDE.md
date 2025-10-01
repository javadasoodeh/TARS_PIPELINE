# Timeout Fix Guide for WrenAI Pipeline

## Problem
The "socket hang up" error was occurring because:
1. **Open WebUI** had a default timeout of 300 seconds (5 minutes)
2. **Pipeline timeout** was set to 60 seconds by default
3. Long-running database queries that take 5+ minutes were being terminated before completion

## Solutions Applied

### 1. Updated TARS_PIPELINE (✅ DONE)

**File**: `TARS_PIPELINE/wrenai_pipeline.py`

#### Changes Made:
- **Default timeout increased**: From 60 to 600 seconds (10 minutes)
  ```python
  WREN_UI_TIMEOUT: int(os.getenv("WREN_UI_TIMEOUT", "600"))
  ```

- **Enhanced request handling**: Added better timeout configuration
  - Connect timeout: 30 seconds
  - Read timeout: 600 seconds
  - Connection keep-alive enabled

- **Improved error handling**: Better error messages for timeout scenarios

- **Retry logic enhanced**: Smarter retry with exponential backoff

### 2. Updated Docker Compose Files (✅ DONE)

**Files**: 
- `docker/docker-compose.yaml`
- `docker/docker-compose-dev.yaml`

#### Changes Made:

**For Open WebUI Service:**
```yaml
environment:
  # Timeout settings for long-running queries (10 minutes)
  - AIOHTTP_CLIENT_TIMEOUT=600
```

**For Pipelines Service:**
```yaml
environment:
  # Timeout settings for long-running operations
  - WREN_UI_TIMEOUT=600
```

## What You Need to Do

### Step 1: Restart Docker Services

You need to restart your Docker containers to apply the changes:

```bash
cd docker
docker-compose down
docker-compose up -d
```

Or if you're using dev setup:
```bash
docker-compose -f docker-compose-dev.yaml down
docker-compose -f docker-compose-dev.yaml up -d
```

### Step 2: Update Pipeline in Open WebUI

1. **Access Open WebUI Admin Panel**:
   - Log in to your Open WebUI instance with an admin account
   - Click on the gear icon (⚙️) in the top-right corner
   - Navigate to **Settings** → **Pipelines** tab

2. **Update the Pipeline**:
   - Find your "WrenAI Database Query Pipeline"
   - Delete the old version or upload the new one from `TARS_PIPELINE/wrenai_pipeline.py`

3. **Configure Valves** (Optional):
   - Open the pipeline settings
   - Check/Update the `WREN_UI_TIMEOUT` valve value to `600` (if not already set)
   - You can adjust this higher if needed (e.g., 900 for 15 minutes)

### Step 3: Verify the Fix

Test with a query that previously failed:

1. Open a new chat in Open WebUI
2. Select your WrenAI pipeline model
3. Ask a complex database question
4. Wait patiently (up to 10 minutes)
5. You should now get results instead of "socket hang up" error

## Additional Configuration Options

### If You Need Even Longer Timeouts:

**For 15 minutes:**
- Update `AIOHTTP_CLIENT_TIMEOUT=900` in docker-compose
- Update `WREN_UI_TIMEOUT=900` in the pipeline valves

**For 30 minutes:**
- Update `AIOHTTP_CLIENT_TIMEOUT=1800` in docker-compose
- Update `WREN_UI_TIMEOUT=1800` in the pipeline valves

### Recommended Timeout Values by Query Complexity:

| Query Type | Recommended Timeout |
|-----------|---------------------|
| Simple queries (< 1000 rows) | 60 seconds |
| Medium queries (1000-10000 rows) | 300 seconds (5 min) |
| Complex queries (10000+ rows) | 600 seconds (10 min) |
| Data warehouse queries | 1800 seconds (30 min) |

## Troubleshooting

### Still Getting Timeout Errors?

1. **Check Wren-UI Service**:
   ```bash
   docker logs wren-ui
   ```

2. **Check Pipeline Logs**:
   ```bash
   docker logs pipelines
   ```

3. **Check Open WebUI Logs**:
   ```bash
   docker logs open-webui
   ```

### Query Takes Too Long?

Consider:
1. **Optimize the database query**
2. **Add database indexes** (see `create_indexes.sql`)
3. **Reduce MAX_ROWS** in pipeline valves
4. **Use more specific questions** to generate simpler queries

### Connection Errors?

Verify all services are running:
```bash
docker ps
```

All these containers should be running:
- wren-ui
- wren-ai-service
- wren-engine
- wren-proxy
- open-webui
- pipelines
- qdrant

## Technical Details

### Timeout Layers Explained:

```
User Query → Open WebUI → Pipelines → Wren-UI → Wren-AI-Service → Database
              (600s)      (600s)      (600s)
```

Each layer needs sufficient timeout to pass the request through.

### Request Flow:

1. **User sends query** to Open WebUI
2. **Open WebUI** routes to Pipelines service (AIOHTTP_CLIENT_TIMEOUT)
3. **Pipeline** calls Wren-UI API (WREN_UI_TIMEOUT)
4. **Wren-UI** processes and queries database
5. **Response** flows back through all layers

All timeout values must be consistent across layers!

## Support

If you continue experiencing issues:
1. Review this guide thoroughly
2. Check all log files mentioned above
3. Ensure all environment variables are properly set
4. Restart all Docker services
5. Clear browser cache and retry

## Summary

✅ **Pipeline Code**: Updated with 600s timeout
✅ **Docker Compose**: Added AIOHTTP_CLIENT_TIMEOUT=600
✅ **Error Handling**: Enhanced retry logic
✅ **Documentation**: Created this guide

**Next Steps**: Restart Docker services and test!

