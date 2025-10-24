# Crawl4AI + Dify Integration - Deployment Guide

## Overview

This guide shows how to deploy both Crawl4AI RAG system and Dify.ai **completely independently** with zero conflicts.

## Architecture

```
┌─────────────────────────────────────┐
│  Dify.ai (Unmodified)               │
│  - docker-db-1 (Dify's PostgreSQL)  │
│  - Uses: /dify/docker/volumes/db/   │
│  - Databases: dify, dify_plugin     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Crawl4AI RAG System                │
│  - postgres-crawl4ai (RAG DB)       │
│  - Uses: crawl4ai_rag_data volume   │
│  - Database: crawl4ai               │
│  - Port: 5432 exposed               │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Dify API Server (dify_api.py)      │
│  - Connects RAG → Dify              │
│  - Port: 5000                       │
└─────────────────────────────────────┘
```

## Prerequisites

- Docker and Docker Compose installed
- Python 3.10+
- Git (for cloning repositories)

---

## Part 1: Deploy Crawl4AI RAG System

### Step 1: Clone or Copy the Repository

```bash
cd /path/to/your/workspace
# Copy your Crawl4AI project files here
```

### Step 2: Create RAG Database Container

```bash
# Create dedicated Docker volume
docker volume create crawl4ai_rag_data

# Start PostgreSQL with pgvector
docker run -d \
  --name postgres-crawl4ai \
  -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=crawl4ai \
  -v crawl4ai_rag_data:/var/lib/postgresql/data \
  --restart unless-stopped \
  pgvector/pgvector:pg15
```

### Step 3: Configure Environment

Create or update `.env`:

```bash
# Database Configuration
POSTGRES_CONTAINER=postgres-crawl4ai
POSTGRES_DATABASE=crawl4ai

# Dify API Configuration
DIFY_API_KEY=your-secret-api-key-here-change-this
KNOWLEDGE_ID=crawl4ai-rag-kb
SEARCH_LEVEL=section
DIFY_API_PORT=5000

# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step 4: Install Python Dependencies

```bash
pip install -r requirements.txt
# Or install manually:
pip install flask python-dotenv google-generativeai sentence-transformers
```

### Step 5: Populate the Database

```bash
# Run workflow to crawl and process documents
python3 workflow_manager.py
```

### Step 6: Start Dify API Server

```bash
# Start the External Knowledge API server
python3 dify_api.py
```

Server will start on: http://localhost:5000

---

## Part 2: Deploy Dify.ai (Standard Installation)

### Step 1: Clone Dify Repository

```bash
cd /path/to/your/workspace
git clone https://github.com/langgenius/dify.git
cd dify/docker
```

### Step 2: Copy Environment File

```bash
cp .env.example .env
# Edit .env if needed (optional)
```

### Step 3: Start Dify

```bash
docker compose up -d
```

**That's it!** Dify will create its own `docker-db-1` container automatically with no conflicts.

### Step 4: Access Dify

Open: http://localhost:8088

Create an admin account on first visit.

---

## Part 3: Connect Crawl4AI to Dify

### Step 1: Verify Dify API Server is Running

```bash
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "knowledge_id": "crawl4ai-rag-kb",
  "search_level": "section"
}
```

### Step 2: Configure External Knowledge in Dify

1. Log in to Dify: http://localhost:8088
2. Navigate to: **Knowledge** → **External Knowledge API**
3. Click: **Add External Knowledge API**
4. Fill in:
   - **Name**: `Crawl4AI RAG System`
   - **API Endpoint**: `http://host.docker.internal:5000/retrieval`
     - *If `host.docker.internal` doesn't work, use your machine's IP*
     - Example: `http://192.168.1.100:5000/retrieval`
   - **API Key**: `your-secret-api-key-here-change-this` (from .env)

5. Click **Test** to verify connection
6. Click **Save**

### Step 3: Use in Applications

1. Create a new **Chatbot** or **Agent** application
2. Add **Knowledge Retrieval** node
3. Select: **Crawl4AI RAG System**
4. Configure:
   - **Top K**: 3-5 chunks
   - **Score Threshold**: 0.6-0.7

---

## Verification Checklist

### ✅ Crawl4AI System

```bash
# Check database is running
docker ps | grep postgres-crawl4ai

# Check database has data
docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -c "SELECT COUNT(*) FROM documents;"

# Check API server
curl http://localhost:5000/health
```

### ✅ Dify System

```bash
# Check all Dify containers
docker ps | grep docker-

# Check Dify database
docker exec docker-db-1 psql -U postgres -l | grep dify

# Access Dify web interface
curl -I http://localhost:8088
```

### ✅ Integration

```bash
# Test retrieval API
curl -X POST http://localhost:5000/retrieval \
  -H "Authorization: Bearer your-secret-api-key-here-change-this" \
  -H "Content-Type: application/json" \
  -d '{"knowledge_id":"crawl4ai-rag-kb","query":"test","retrieval_setting":{"top_k":2}}'
```

---

## Container Summary

| Container Name | Image | Purpose | Port | Volume |
|----------------|-------|---------|------|--------|
| `postgres-crawl4ai` | pgvector/pgvector:pg15 | RAG Database | 5432 | crawl4ai_rag_data |
| `docker-db-1` | postgres:15-alpine | Dify Database | - | ./volumes/db/data |
| `docker-api-1` | langgenius/dify-api | Dify API | 5001 | - |
| `docker-web-1` | langgenius/dify-web | Dify Web | 8088 | - |
| `docker-worker-1` | langgenius/dify-api | Dify Worker | - | - |

**Key Point**: `postgres-crawl4ai` and `docker-db-1` are completely separate!

---

## Production Deployment

### Security Recommendations

1. **Change API Keys**:
   ```bash
   # Generate strong API key
   openssl rand -hex 32
   ```

2. **Use HTTPS**: Deploy behind nginx/traefik with SSL

3. **Restrict Database Access**:
   ```bash
   # Don't expose port 5432 in production
   docker run -d --name postgres-crawl4ai \
     -e POSTGRES_PASSWORD=strong_password \
     -v crawl4ai_rag_data:/var/lib/postgresql/data \
     pgvector/pgvector:pg15
   # No -p 5432:5432
   ```

4. **Use Production WSGI Server**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 dify_api:app
   ```

### Backup Strategy

```bash
# Backup Crawl4AI RAG database
docker exec postgres-crawl4ai pg_dump -U postgres crawl4ai > crawl4ai_backup.sql

# Backup Dify database
docker exec docker-db-1 pg_dump -U postgres dify > dify_backup.sql

# Backup Docker volumes
docker run --rm -v crawl4ai_rag_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/crawl4ai_data.tar.gz -C /data .
```

---

## Troubleshooting

### Issue: "docker-db-1 already exists"

**This means Dify is already running** - no action needed! This is the correct state.

### Issue: Port 5432 already in use

```bash
# Check what's using port 5432
sudo lsof -i :5432

# If it's another PostgreSQL, either:
# 1. Stop it, or
# 2. Change Crawl4AI port:
docker run -d --name postgres-crawl4ai -p 5433:5432 ...
# Then update DATABASE_URL in .env to use port 5433
```

### Issue: Dify can't connect to External Knowledge API

**Solutions**:

1. **Check API is running**: `curl http://localhost:5000/health`

2. **Try different endpoint URLs**:
   - `http://host.docker.internal:5000/retrieval` (Docker Desktop)
   - `http://172.17.0.1:5000/retrieval` (Docker bridge IP)
   - `http://YOUR_MACHINE_IP:5000/retrieval` (Your actual IP)

3. **Find your machine's IP**:
   ```bash
   hostname -I | awk '{print $1}'
   ```

### Issue: Database data lost after restart

**Cause**: Container removed without volume

**Solution**: Always use `-v` flag when creating containers. Volumes persist even if container is removed.

---

## Deployment on New Machine

### Quick Setup Script

Create `deploy.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Deploying Crawl4AI + Dify Integration"

# 1. Create RAG database
echo "📦 Creating RAG database..."
docker volume create crawl4ai_rag_data
docker run -d \
  --name postgres-crawl4ai \
  -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=crawl4ai \
  -v crawl4ai_rag_data:/var/lib/postgresql/data \
  --restart unless-stopped \
  pgvector/pgvector:pg15

# 2. Wait for database
sleep 5

# 3. Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt

# 4. Start Dify API server
echo "🌐 Starting Dify API server..."
python3 dify_api.py &

# 5. Deploy Dify (if not already)
if [ ! -d "dify" ]; then
    echo "📥 Cloning Dify..."
    git clone https://github.com/langgenius/dify.git
    cd dify/docker
    cp .env.example .env
    docker compose up -d
    cd ../..
fi

echo "✅ Deployment complete!"
echo ""
echo "📍 Services:"
echo "   Crawl4AI API: http://localhost:5000"
echo "   Dify Web UI:  http://localhost:8088"
echo ""
echo "📚 Next steps:"
echo "   1. Run: python3 workflow_manager.py (to populate database)"
echo "   2. Open Dify and configure External Knowledge API"
```

Make executable and run:
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## Summary

✅ **Crawl4AI RAG**: Uses `postgres-crawl4ai` container + `crawl4ai_rag_data` volume

✅ **Dify**: Uses standard `docker-db-1` container + bind mount volumes

✅ **No Conflicts**: Different names, different volumes, completely independent

✅ **Easy Deployment**: No modifications to Dify's docker-compose needed

✅ **Portable**: Move to any machine - just create `postgres-crawl4ai` first

---

## Support

- Crawl4AI Issues: Check application logs
- Dify Issues: https://github.com/langgenius/dify/issues
- API Integration: See `DIFY_INTEGRATION_GUIDE.md`
