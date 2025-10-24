# Database Guide

Complete guide for PostgreSQL database operations.

## Quick Start

### Start Database
```bash
docker start postgres-crawl4ai
```

### Check Status
```bash
./scripts/db_status.sh
```

### Search Database
```bash
./scripts/db_search.sh "smart contracts"
```

## Database Shell Scripts

### db_status.sh
Shows database overview
```bash
./scripts/db_status.sh

# Output:
# Documents: 25
# Sections: 150
# Propositions: 450
# Total embeddings: 625
```

### db_list.sh
List all documents
```bash
./scripts/db_list.sh

# Shows: ID, Title, Created date
```

### db_detail.sh <doc_id>
Show document details
```bash
./scripts/db_detail.sh doc_abc123

# Shows full document with sections and propositions
```

### db_search.sh <query>
Search by similarity
```bash
./scripts/db_search.sh "deploy contracts"

# Returns top 5 matches with similarity scores
```

### db_watch.sh
Monitor database in real-time
```bash
./scripts/db_watch.sh

# Updates every 2 seconds
```

## Search Levels

### Document Level
High-level overview search
```python
from embedding_search import EmbeddingSearcher
searcher = EmbeddingSearcher()
results = searcher.search_documents("query", top_k=5, level="document")
```

### Section Level (Recommended)
Balanced detail and context
```python
results = searcher.search_documents("query", top_k=10, level="section")
```

### Proposition Level
Atomic facts, high precision
```python
results = searcher.search_documents("query", top_k=20, level="proposition")
```

## Database Schema

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    mode TEXT DEFAULT 'paragraph',
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding vector(768)
);

-- Sections table
CREATE TABLE semantic_sections (
    id TEXT PRIMARY KEY,
    document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    position INTEGER,
    embedding vector(768)
);

-- Propositions table
CREATE TABLE semantic_propositions (
    id TEXT PRIMARY KEY,
    section_id TEXT REFERENCES semantic_sections(id) ON DELETE CASCADE,
    document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    position INTEGER,
    embedding vector(768)
);

-- HNSW indexes for fast search
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON semantic_sections USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON semantic_propositions USING hnsw (embedding vector_cosine_ops);
```

## Performance

### HNSW Index Benefits
- **Without HNSW**: 2-10 seconds (full scan)
- **With HNSW**: 10-50ms (200-600× faster!)

### Search Performance
```
10,000 documents search:
- Document level: ~10ms
- Section level: ~30ms
- Proposition level: ~50ms
```

## Backup & Restore

### Backup
```bash
docker exec postgres-crawl4ai pg_dump -U postgres crawl4ai > backup.sql
```

### Restore
```bash
cat backup.sql | docker exec -i postgres-crawl4ai psql -U postgres -d crawl4ai
```

## Troubleshooting

### Database Not Running
```bash
docker start postgres-crawl4ai
docker ps | grep postgres-crawl4ai
```

### Connection Failed
```bash
# Check container is running
docker inspect postgres-crawl4ai

# Check port mapping
docker port postgres-crawl4ai

# Test connection
docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -c "SELECT 1;"
```

### Reset Database
```bash
# Stop and remove container
docker stop postgres-crawl4ai
docker rm postgres-crawl4ai

# Recreate with fresh schema
docker run -d --name postgres-crawl4ai \
  -e POSTGRES_DB=crawl4ai \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Load schema
cat schema_complete.sql | docker exec -i postgres-crawl4ai \
  psql -U postgres -d crawl4ai
```
