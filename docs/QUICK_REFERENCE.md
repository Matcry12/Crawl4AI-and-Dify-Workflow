# Quick Reference Guide 🚀

**Your complete command reference for monitoring and managing the RAG system**

---

## Database Monitoring Scripts

### Quick Status
```bash
./scripts/db_status.sh
```
Shows: Documents, sections, propositions, embeddings, coverage, size

### Watch in Real-time
```bash
./scripts/db_watch.sh
```
Auto-refreshes every 2 seconds. Press Ctrl+C to stop.

### List All Documents
```bash
./scripts/db_list.sh
```
Shows all documents with their chunk counts

### Search Documents
```bash
./scripts/db_search.sh <keyword>
```
Example: `./scripts/db_search.sh blockchain`

### Document Details
```bash
./scripts/db_detail.sh <document_id>
```
Shows complete details: sections, propositions, embeddings

---

## One-Line Commands

### Quick Status
```bash
docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -c "
SELECT COUNT(*) as docs FROM documents;
SELECT COUNT(*) as sections FROM semantic_sections;
SELECT COUNT(*) as props FROM semantic_propositions;
SELECT COUNT(*) as embeddings FROM embeddings;
"
```

### List Documents
```bash
docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -c "
SELECT id, title, mode FROM documents ORDER BY created_at DESC;
"
```

### Database Size
```bash
docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -c "
SELECT pg_size_pretty(pg_database_size('crawl4ai'));
"
```

### Clear Database
```bash
docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -c "
TRUNCATE TABLE documents CASCADE;
TRUNCATE TABLE embeddings;
"
```

---

## Workflow Commands

### Run Complete Workflow
```bash
python3 workflow_manager.py
```

### Test Embedding Search
```bash
python3 test_embedding_search_simple.py
```

### Test Hybrid Chunker
```bash
python3 test_hybrid_chunker.py
```

---

## Docker Commands

### Container Status
```bash
docker ps | grep db-1
```

### Container Logs
```bash
docker logs postgres-crawl4ai --tail 50
docker logs postgres-crawl4ai --follow  # Follow in real-time
```

### Container Resources
```bash
docker stats postgres-crawl4ai --no-stream
```

### Restart Container
```bash
docker restart postgres-crawl4ai
```

### Enter Container
```bash
docker exec -it docker-db-1 bash
```

### PostgreSQL CLI
```bash
docker exec -it docker-db-1 psql -U postgres -d crawl4ai
```

---

## Common Queries

### Documents with Most Chunks
```bash
docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -c "
SELECT
    d.title,
    d.mode,
    COUNT(DISTINCT s.id) as sections,
    COUNT(DISTINCT p.id) as propositions
FROM documents d
LEFT JOIN semantic_sections s ON s.document_id = d.id
LEFT JOIN semantic_propositions p ON p.section_id = s.id
GROUP BY d.id, d.title, d.mode
ORDER BY COUNT(DISTINCT p.id) DESC
LIMIT 10;
"
```

### Recent Activity (Last Hour)
```bash
docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -c "
SELECT
    title,
    mode,
    created_at
FROM documents
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
"
```

### Embedding Coverage
```bash
docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -c "
SELECT
    entity_type,
    COUNT(*) as count
FROM embeddings
GROUP BY entity_type;
"
```

### Documents Without Chunks (Should be 0)
```bash
docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -c "
SELECT
    d.id,
    d.title,
    d.mode
FROM documents d
LEFT JOIN semantic_sections s ON s.document_id = d.id
WHERE s.id IS NULL;
"
```

---

## File Locations

### Configuration
- `.env` - Environment variables
- `.env.example` - Configuration template

### Code
- `workflow_manager.py` - Main workflow orchestration
- `document_creator.py` - Document creation
- `document_merger.py` - Document merging
- `hybrid_chunker.py` - Semantic chunking
- `embedding_search.py` - Similarity search
- `extract_topics.py` - Topic extraction

### Database
- `chunked_document_database.py` - Database operations
- `document_database_docker.py` - Docker database handler
- `schema_complete_optimized.sql` - Database schema

### Output
- `bfs_crawled/` - Crawl results
- `documents/` - Generated documents
- `merged_documents/` - Merged documents

### Scripts
- `scripts/db_status.sh` - Quick status
- `scripts/db_watch.sh` - Real-time monitoring
- `scripts/db_list.sh` - List all documents
- `scripts/db_search.sh` - Search documents
- `scripts/db_detail.sh` - Document details

---

## Configuration Settings

### Rate Limiting
```bash
ENABLE_RATE_LIMITING=true
API_DELAY_SECONDS=4.5        # LLM calls
EMBEDDING_DELAY_SECONDS=0.1  # Embedding calls
```

### Database
```bash
USE_POSTGRESQL=true
POSTGRES_CONTAINER=docker-db-1
POSTGRES_DATABASE=crawl4ai
```

### Models
```bash
LLM: gemini-2.5-flash-lite
Embedding: text-embedding-004 (768 dimensions)
```

---

## Troubleshooting

### Database not responding?
```bash
docker restart postgres-crawl4ai
```

### Check container logs
```bash
docker logs postgres-crawl4ai --tail 100
```

### Check PostgreSQL processes
```bash
docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -c "
SELECT * FROM pg_stat_activity WHERE datname = 'crawl4ai';
"
```

### Vacuum database
```bash
docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -c "VACUUM ANALYZE;"
```

### Reset everything
```bash
# Clear database
docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -c "
TRUNCATE TABLE documents CASCADE;
TRUNCATE TABLE embeddings;
"

# Clear output directories
rm -rf bfs_crawled/* merged_documents/* documents/*
```

---

## Useful Aliases

Add to `~/.bashrc`:

```bash
# Quick database status
alias db='cd ~/Documents/Crawl4AI && ./scripts/db_status.sh'

# Watch database
alias db-watch='cd ~/Documents/Crawl4AI && ./scripts/db_watch.sh'

# List documents
alias db-list='cd ~/Documents/Crawl4AI && ./scripts/db_list.sh'

# Search
alias db-search='cd ~/Documents/Crawl4AI && ./scripts/db_search.sh'

# Run workflow
alias crawl='cd ~/Documents/Crawl4AI && python3 workflow_manager.py'

# PostgreSQL CLI
alias psql-crawl='docker exec -it docker-db-1 psql -U postgres -d crawl4ai'
```

Reload: `source ~/.bashrc`

Usage:
```bash
db              # Quick status
db-watch        # Watch in real-time
db-list         # List all documents
db-search xyz   # Search for "xyz"
crawl           # Run workflow
psql-crawl      # Enter PostgreSQL CLI
```

---

## Expected Results

### After First Crawl (3 topics)

```
Documents:     6 (3 paragraph + 3 full-doc)
Sections:      ~15
Propositions:  ~70
Embeddings:    ~91
Time:          ~2.7 minutes (with rate limiting)
```

### After Second Crawl (Same URL)

```
Documents:     6 (merged, not duplicated)
Sections:      ~15 (updated)
Propositions:  ~70 (updated)
Embeddings:    ~91 (updated)
Time:          ~1 minute (merge is faster)
```

---

## Important Notes

✅ **Rate limiting is enabled** - Protects free tier API (4.5s delay)
✅ **Hybrid chunking is applied** - Both create and merge paths
✅ **Embedding search works** - Prevents duplicates (>0.85 similarity)
✅ **3-level hierarchy** - Documents → Sections → Propositions
✅ **All embeddings are 768-dim** - From text-embedding-004

---

## Getting Help

### Documentation Files
- `DATABASE_MONITORING_GUIDE.md` - Complete monitoring guide
- `RATE_LIMITING_GUIDE.md` - Rate limiting explanation
- `EMBEDDING_SEARCH_TEST_RESULTS.md` - Search functionality
- `HYBRID_CHUNKING_FIX_COMPLETE.md` - Chunking implementation
- `MODEL_CONFIGURATION.md` - Model settings

### Quick Help
```bash
# List all markdown docs
ls *.md

# Read a specific guide
cat DATABASE_MONITORING_GUIDE.md
```

---

**Your complete quick reference is ready!** 📚

Everything you need to monitor, manage, and troubleshoot your RAG system! 🚀
