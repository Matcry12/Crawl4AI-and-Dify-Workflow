# Dify Integration Guide

Complete guide for integrating Crawl4AI with Dify.ai as an External Knowledge API.

## Quick Setup

### 1. Start Dify API Server
```bash
# Starts Flask API on port 5000
python3 dify_api.py
```

### 2. Configure in Dify
1. Go to **Knowledge Base** → **External Knowledge API**
2. Enter API endpoint: `http://localhost:5000/retrieval`
3. Enter API key from `.env`: `DIFY_API_KEY`
4. Test connection

### 3. Environment Variables
```bash
# .env file
DIFY_API_KEY=your-secret-api-key
KNOWLEDGE_ID=crawl4ai-rag-kb
SEARCH_LEVEL=section          # document, section, or proposition
DIFY_API_PORT=5000
```

## Architecture

```
Dify Docker Network
  ↓
Your Flask API (dify_api.py:5000)
  ↓
PostgreSQL Database (postgres-crawl4ai:5432)
  ↓
Vector Search with pgvector
```

## Common Issues

### Issue 1: Connection Refused
**Symptom**: Dify shows "Connection refused"

**Solution**:
```bash
# Check if API is running
curl http://localhost:5000/retrieval

# Start API if not running
python3 dify_api.py
```

### Issue 2: Network Not Accessible
**Symptom**: "Network error" in Dify

**Cause**: Dify Docker containers can't reach `localhost:5000`

**Solution**: Use host network mode
```bash
# In docker-compose.yml
services:
  api:
    network_mode: host  # Use host network
```

Or use container IP:
```bash
# Get your machine's IP
ip addr show | grep "inet "

# Use in Dify: http://192.168.x.x:5000/retrieval
```

### Issue 3: Database Connection Failed
**Symptom**: API returns 500 error

**Solution**:
```bash
# Check database is running
docker ps | grep postgres-crawl4ai

# Start if needed
docker start postgres-crawl4ai

# Test connection
./scripts/db_status.sh
```

## API Endpoints

### POST /retrieval
Search knowledge base

**Request**:
```json
{
  "knowledge_id": "crawl4ai-rag-kb",
  "query": "How to deploy smart contracts?",
  "retrieval_setting": {
    "top_k": 5,
    "score_threshold": 0.7
  }
}
```

**Response**:
```json
{
  "records": [
    {
      "content": "Smart contract deployment...",
      "score": 0.92,
      "title": "Deploy Smart Contracts",
      "metadata": {
        "document_id": "doc_123",
        "source_url": "https://example.com"
      }
    }
  ]
}
```

## Advanced Configuration

### Search Levels
```bash
SEARCH_LEVEL=document      # High-level overview
SEARCH_LEVEL=section       # Balanced (recommended)
SEARCH_LEVEL=proposition   # Detailed, atomic facts
```

### Performance Tuning
```bash
# Adjust retrieval count
top_k=10  # Return more results

# Adjust similarity threshold
score_threshold=0.6  # Lower = more results, less accurate
score_threshold=0.8  # Higher = fewer results, more accurate
```

## Testing

```bash
# Test API directly
curl -X POST http://localhost:5000/retrieval \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_id": "crawl4ai-rag-kb",
    "query": "test query",
    "retrieval_setting": {"top_k": 3}
  }'
```

For more details, see `dify_api.py` source code.
