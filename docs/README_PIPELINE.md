# Crawl4AI RAG Pipeline - Quick Reference

One script to rule them all! 🚀

---

## ⚡ Quick Start

```bash
# Start everything (database + API + UI)
./run_rag_pipeline.sh start

# Open in browser
google-chrome http://localhost:5001
```

**That's it!** Everything is running.

---

## 📋 Common Commands

```bash
# Start all services
./run_rag_pipeline.sh start

# Stop all services
./run_rag_pipeline.sh stop

# Check status
./run_rag_pipeline.sh status

# View logs
./run_rag_pipeline.sh logs-ui
./run_rag_pipeline.sh logs-api

# Interactive menu
./run_rag_pipeline.sh
```

---

## 🌐 URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Web UI | http://localhost:5001 | Main interface |
| API | http://localhost:5005 | Retrieval endpoint |
| Database | localhost:5432 | PostgreSQL |

---

## 🎯 Workflow

1. **Start**: `./run_rag_pipeline.sh start`
2. **Open**: http://localhost:5001
3. **Crawl**: Workflow tab → Configure → Start
4. **View**: Documents tab → Show Full Details
5. **Stop**: `./run_rag_pipeline.sh stop`

---

## 📖 Full Documentation

See **PIPELINE_GUIDE.md** for complete documentation including:
- All commands and options
- Troubleshooting guide
- Configuration details
- Example workflows
- Advanced usage

---

## 🆘 Help

```bash
./run_rag_pipeline.sh help
```

---

**Enjoy!** 🎉
