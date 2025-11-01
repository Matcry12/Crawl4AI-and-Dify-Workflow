# Crawl4AI Documentation

## 📚 Documentation Index

### Getting Started
- **[../README.md](../README.md)** - Main project README
- **[../QUICK_REFERENCE.md](../QUICK_REFERENCE.md)** - Quick reference guide

### Architecture & Design
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and workflow
- **[CHUNKING_AND_RETRIEVAL_DIAGRAM.md](CHUNKING_AND_RETRIEVAL_DIAGRAM.md)** - Visual diagram of chunking/retrieval

### Database & Search
- **[DATABASE.md](DATABASE.md)** - Database operations, search, and monitoring

### Integration
- **[DIFY_SETUP.md](DIFY_SETUP.md)** - Dify.ai integration guide

### Deployment
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Production deployment guide

### Development
- **[ALL_FIXES_SUMMARY.md](ALL_FIXES_SUMMARY.md)** - Critical fixes and improvements

## 🚀 Quick Links

### Common Tasks

**Start the system:**
```bash
# 1. Start database
docker start postgres-crawl4ai

# 2. Run workflow
python3 workflow_manager.py
```

**Check database:**
```bash
./scripts/db_status.sh
./scripts/db_search.sh "your query"
```

**Start Dify API:**
```bash
python3 dify_api.py
```

### Configuration

All configuration in `.env` file:
```bash
# Copy example
cp .env.example .env

# Edit with your settings
nano .env
```

Key variables:
- `GEMINI_API_KEY` - Your Gemini API key
- `CHUNKING_MODEL` - Model for chunking
- `TOPIC_EXTRACTION_MODEL` - Model for extraction
- Database connection settings

## 📖 Documentation Guide

### For Users
1. Start with [README.md](../README.md)
2. Use [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) for commands
3. See [DATABASE.md](DATABASE.md) for search operations

### For Developers
1. Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design
2. Review [ALL_FIXES_SUMMARY.md](ALL_FIXES_SUMMARY.md) for known issues
3. Check [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for production setup

### For Integration
1. Follow [DIFY_SETUP.md](DIFY_SETUP.md) for Dify integration
2. See [DATABASE.md](DATABASE.md) for direct database access

## 🆘 Need Help?

1. Check [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) for common commands
2. See [DATABASE.md](DATABASE.md) for database troubleshooting
3. Review [DIFY_SETUP.md](DIFY_SETUP.md) for integration issues
4. Check [ALL_FIXES_SUMMARY.md](ALL_FIXES_SUMMARY.md) for known fixes
