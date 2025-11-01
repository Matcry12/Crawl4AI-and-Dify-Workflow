# RAG Pipeline Quick Start Guide

Complete guide for running your Crawl4AI RAG pipeline with database, API, and Web UI.

---

## 🚀 Quick Start (One Command)

```bash
./run_rag_pipeline.sh start
```

This starts **everything**:
- ✅ PostgreSQL database (with pgvector)
- ✅ Dify API server (port 5005)
- ✅ Web UI (port 5001)

Then open in your browser: **http://localhost:5001**

---

## 📋 All Available Commands

### Main Commands

```bash
# Start everything
./run_rag_pipeline.sh start

# Stop everything
./run_rag_pipeline.sh stop

# Restart everything
./run_rag_pipeline.sh restart

# Check status of all services
./run_rag_pipeline.sh status
```

### Individual Services

```bash
# Start only database
./run_rag_pipeline.sh start-db

# Start only Dify API
./run_rag_pipeline.sh start-api

# Start only Web UI
./run_rag_pipeline.sh start-ui

# Stop individual services
./run_rag_pipeline.sh stop-db
./run_rag_pipeline.sh stop-api
./run_rag_pipeline.sh stop-ui
```

### View Logs

```bash
# Watch Web UI logs (live)
./run_rag_pipeline.sh logs-ui

# Watch Dify API logs (live)
./run_rag_pipeline.sh logs-api
```

### Interactive Menu

```bash
# Show interactive menu with options
./run_rag_pipeline.sh menu

# Or just run without arguments
./run_rag_pipeline.sh
```

---

## 🎯 Common Workflows

### 1. First Time Setup

```bash
# Start everything
./run_rag_pipeline.sh start

# Check all services are running
./run_rag_pipeline.sh status

# Open Web UI
# Browser: http://localhost:5001
```

### 2. Daily Usage

```bash
# Start services
./run_rag_pipeline.sh start

# Run a crawl via Web UI
# Browser: http://localhost:5001 → Workflow tab

# Stop when done
./run_rag_pipeline.sh stop
```

### 3. Debugging Issues

```bash
# Check status
./run_rag_pipeline.sh status

# View logs in real-time
./run_rag_pipeline.sh logs-ui

# Or for API issues
./run_rag_pipeline.sh logs-api

# Restart if needed
./run_rag_pipeline.sh restart
```

---

## 🌐 Access Points

After running `./run_rag_pipeline.sh start`:

| Service | URL | Purpose |
|---------|-----|---------|
| **Web UI** | http://localhost:5001 | Main interface - run crawls, view docs |
| **Dify API** | http://localhost:5005 | Retrieval endpoint for RAG queries |
| **Database** | localhost:5432 | PostgreSQL with pgvector |

---

## 📊 Web UI Features

### Workflow Tab (Main)

Configure and run crawling workflows:
- Set start URL
- Choose number of pages (1-100)
- Select LLM model
- Enable/disable pipeline stages
- Watch **live console logs** during crawl
- See progress in real-time

### Documents Tab

Browse all documents in database:
- Click "Show Full Details" to expand
- See full content, keywords, and chunks
- Search documents with search box
- Yellow highlighted chunks for easy viewing

### Statistics Tab

View database metrics:
- Total documents count
- Total chunks count
- Average chunks per document
- Database connection status

---

## 🔧 Configuration

### Environment Variables

The script reads from `.env` file:

```bash
# Required
GEMINI_API_KEY=your-key-here

# Optional (has defaults)
DIFY_API_KEY=testing
DIFY_API_PORT=5005
WEB_UI_PORT=5001
```

### Changing Ports

Edit the script variables at the top:

```bash
POSTGRES_PORT="5432"
DIFY_API_PORT="5005"
WEB_UI_PORT="5001"
```

---

## 📁 Log Files

Logs are automatically saved to `logs/` directory:

```bash
logs/
├── web_ui.log      # Web UI output
└── dify_api.log    # Dify API output
```

View logs:
```bash
# Live tail
tail -f logs/web_ui.log
tail -f logs/dify_api.log

# Or use script commands
./run_rag_pipeline.sh logs-ui
./run_rag_pipeline.sh logs-api
```

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check status
./run_rag_pipeline.sh status

# View logs for errors
./run_rag_pipeline.sh logs-ui

# Try restart
./run_rag_pipeline.sh restart
```

### Port Already in Use

```bash
# Find what's using the port
lsof -i :5001  # Web UI
lsof -i :5005  # Dify API
lsof -i :5432  # Database

# Kill process
kill -9 <PID>

# Or stop with script
./run_rag_pipeline.sh stop
```

### Database Not Responding

```bash
# Check Docker
docker ps | grep postgres-crawl4ai

# Restart database
./run_rag_pipeline.sh stop-db
./run_rag_pipeline.sh start-db

# Check logs
docker logs postgres-crawl4ai
```

### Web UI Shows Errors

```bash
# Check GEMINI_API_KEY is set in .env
grep GEMINI_API_KEY .env

# View UI logs
./run_rag_pipeline.sh logs-ui

# Restart UI
./run_rag_pipeline.sh stop-ui
./run_rag_pipeline.sh start-ui
```

---

## 🎓 Example Workflow

### Complete Example: Crawl EOS Docs

```bash
# 1. Start services
./run_rag_pipeline.sh start

# Expected output:
# ✅ Database started
# ✅ Dify API started (PID: 12345)
# ✅ Web UI started (PID: 12346)
# 🎉 All services are running!

# 2. Check status
./run_rag_pipeline.sh status

# Expected output:
# ✅ Database is running
#    Documents: 25
#    Chunks: 58
# ✅ Dify API is running (PID: 12345)
# ✅ Web UI is running (PID: 12346)

# 3. Open Web UI in browser
# http://localhost:5001

# 4. In Web UI:
#    - Go to "Workflow" tab
#    - URL: https://docs.eosnetwork.com/docs/latest/quick-start/
#    - Max pages: 3
#    - LLM: gemini-2.5-flash-lite
#    - All checkboxes: enabled
#    - Click "Start Workflow"

# 5. Watch live logs in UI (or terminal)
./run_rag_pipeline.sh logs-ui

# 6. When done, view documents
#    - Click "Documents" tab
#    - Click "Show Full Details" on any document
#    - See chunks highlighted in yellow

# 7. Stop services when finished
./run_rag_pipeline.sh stop

# Expected output:
# ✅ Web UI stopped
# ✅ Dify API stopped
# ✅ Database stopped
```

---

## 🔄 Daily Development Workflow

### Morning

```bash
# Start services
./run_rag_pipeline.sh start

# Open Web UI
google-chrome http://localhost:5001 &
```

### During Work

```bash
# Run crawls via Web UI
# Check logs if issues occur
./run_rag_pipeline.sh logs-ui

# Check database status
./run_rag_pipeline.sh status
```

### Evening

```bash
# Stop services
./run_rag_pipeline.sh stop
```

---

## 📖 Interactive Menu

For a visual menu interface:

```bash
./run_rag_pipeline.sh
```

Or:

```bash
./run_rag_pipeline.sh menu
```

You'll see:

```
================================================================================
🤖 RAG Pipeline Manager
================================================================================

Select an option:

  1) Start all services
  2) Stop all services
  3) Restart all services
  4) Check status

  5) Start database only
  6) Start Dify API only
  7) Start Web UI only

  8) View Web UI logs
  9) View Dify API logs

  0) Exit

Enter choice:
```

---

## 🚀 Advanced Usage

### Run in Background

```bash
# Start and detach
./run_rag_pipeline.sh start

# Services run in background
# Web UI and API write to logs/

# Check status anytime
./run_rag_pipeline.sh status
```

### Auto-Start on Boot

Add to crontab:

```bash
crontab -e

# Add line:
@reboot /path/to/Crawl4AI/run_rag_pipeline.sh start
```

### Custom Workflow via API

```bash
# Ensure services are running
./run_rag_pipeline.sh status

# Test retrieval API
curl -X POST http://localhost:5005/retrieval \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer testing" \
  -d '{
    "knowledge_id": "crawl4ai-rag-kb",
    "query": "How to create smart contracts",
    "top_k": 5
  }'
```

---

## 📝 What Each Service Does

### PostgreSQL Database
- Stores all documents and chunks
- Uses pgvector extension for embeddings
- Parent Document Retrieval architecture
- Persists data across restarts

### Dify API (Port 5005)
- RESTful API for document retrieval
- Handles embedding search
- Compatible with Dify.ai specification
- Used by Web UI and external tools

### Web UI (Port 5001)
- Main user interface
- Workflow configuration and execution
- Document browsing with expandable details
- Live log viewing during crawls
- Statistics dashboard

---

## 🎯 Next Steps

1. **Run your first crawl**:
   ```bash
   ./run_rag_pipeline.sh start
   # Open http://localhost:5001
   # Go to Workflow tab → Start Workflow
   ```

2. **Browse documents**:
   ```bash
   # Documents tab → Click "Show Full Details"
   # See highlighted chunks
   ```

3. **Check quality**:
   ```bash
   # Statistics tab → View metrics
   # Documents tab → Search and explore
   ```

4. **Integrate with your app**:
   ```bash
   # Use API at http://localhost:5005/retrieval
   # Send queries, get relevant documents
   ```

---

## 💡 Tips

- ✅ Always check status before starting: `./run_rag_pipeline.sh status`
- ✅ Use logs for debugging: `./run_rag_pipeline.sh logs-ui`
- ✅ Database persists between restarts (Docker volume)
- ✅ Web UI shows live logs during crawls
- ✅ Yellow highlighted chunks make viewing easy
- ✅ Test document has 0 score - should delete it

---

## 🆘 Getting Help

```bash
# Show help
./run_rag_pipeline.sh help

# Check what's running
./run_rag_pipeline.sh status

# View logs for errors
./run_rag_pipeline.sh logs-ui
./run_rag_pipeline.sh logs-api
```

---

**Enjoy your RAG pipeline!** 🎉

Quick start: `./run_rag_pipeline.sh start` → Open http://localhost:5001
