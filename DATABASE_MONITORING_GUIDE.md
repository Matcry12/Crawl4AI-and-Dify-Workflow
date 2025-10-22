# Database Monitoring Guide 📊

**Date**: 2025-10-22
**Purpose**: Complete guide to watch, monitor, and inspect your PostgreSQL database
**Database**: crawl4ai (PostgreSQL in Docker)

---

## Table of Contents

1. [Quick Status Check](#quick-status-check)
2. [Document Statistics](#document-statistics)
3. [Chunk Statistics](#chunk-statistics)
4. [Embedding Statistics](#embedding-statistics)
5. [Search & Query](#search--query)
6. [Real-time Monitoring](#real-time-monitoring)
7. [Performance Metrics](#performance-metrics)
8. [Troubleshooting](#troubleshooting)

---

## Quick Status Check

### One-Line Overview

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    (SELECT COUNT(*) FROM documents) as documents,
    (SELECT COUNT(*) FROM semantic_sections) as sections,
    (SELECT COUNT(*) FROM semantic_propositions) as propositions,
    (SELECT COUNT(*) FROM embeddings) as embeddings;
"
```

**Output**:
```
documents | sections | propositions | embeddings
----------+----------+--------------+------------
        6 |       15 |           70 |         91
```

### Container Status

```bash
# Check if PostgreSQL container is running
docker ps | grep db-1

# Check container logs
docker logs docker-db-1 --tail 50

# Check container resources
docker stats docker-db-1 --no-stream
```

---

## Document Statistics

### All Documents Overview

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    id,
    title,
    mode,
    category,
    LENGTH(content) as content_length,
    created_at
FROM documents
ORDER BY created_at DESC;
"
```

**Output**:
```
id                               | title                    | mode      | category | content_length | created_at
---------------------------------+--------------------------+-----------+----------+----------------+------------
smart_contract_dev_full-doc      | EOS Smart Contracts      | full-doc  | tutorial |           6479 | 2025-10-22
smart_contract_dev_paragraph     | EOS Smart Contracts      | paragraph | tutorial |            619 | 2025-10-22
```

### Documents with Chunk Count

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    d.id,
    d.title,
    d.mode,
    COUNT(DISTINCT s.id) as sections,
    COUNT(DISTINCT p.id) as propositions
FROM documents d
LEFT JOIN semantic_sections s ON s.document_id = d.id
LEFT JOIN semantic_propositions p ON p.section_id = s.id
GROUP BY d.id, d.title, d.mode
ORDER BY d.created_at DESC;
"
```

**Output**:
```
id                          | title                | mode      | sections | propositions
----------------------------+----------------------+-----------+----------+--------------
smart_contract_dev_full-doc | EOS Smart Contracts  | full-doc  |        5 |           24
smart_contract_dev_paragraph| EOS Smart Contracts  | paragraph |        1 |            4
```

### Documents by Mode

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    mode,
    COUNT(*) as count,
    AVG(LENGTH(content))::int as avg_content_length
FROM documents
GROUP BY mode;
"
```

### Documents by Category

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    category,
    COUNT(*) as count,
    COUNT(DISTINCT mode) as modes
FROM documents
GROUP BY category
ORDER BY count DESC;
"
```

---

## Chunk Statistics

### Sections Overview

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    s.id,
    s.document_id,
    d.title as document_title,
    s.header,
    s.section_index,
    LENGTH(s.content) as content_length,
    COUNT(p.id) as proposition_count
FROM semantic_sections s
JOIN documents d ON s.document_id = d.id
LEFT JOIN semantic_propositions p ON p.section_id = s.id
GROUP BY s.id, s.document_id, d.title, s.header, s.section_index
ORDER BY d.title, s.section_index;
"
```

### Propositions Overview

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    p.id,
    d.title as document,
    s.header as section,
    p.proposition_index,
    LEFT(p.content, 80) as content_preview,
    p.proposition_type
FROM semantic_propositions p
JOIN semantic_sections s ON p.section_id = s.id
JOIN documents d ON s.document_id = d.id
ORDER BY d.title, s.section_index, p.proposition_index
LIMIT 20;
"
```

### Chunk Size Distribution

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    'sections' as type,
    MIN(LENGTH(content)) as min_chars,
    AVG(LENGTH(content))::int as avg_chars,
    MAX(LENGTH(content)) as max_chars,
    COUNT(*) as total_count
FROM semantic_sections
UNION ALL
SELECT
    'propositions',
    MIN(LENGTH(content)),
    AVG(LENGTH(content))::int,
    MAX(LENGTH(content)),
    COUNT(*)
FROM semantic_propositions;
"
```

**Output**:
```
type          | min_chars | avg_chars | max_chars | total_count
--------------+-----------+-----------+-----------+-------------
sections      |       450 |       850 |      1500 |          15
propositions  |       120 |       350 |       580 |          70
```

### Propositions by Type

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    proposition_type,
    COUNT(*) as count,
    AVG(LENGTH(content))::int as avg_length
FROM semantic_propositions
GROUP BY proposition_type
ORDER BY count DESC;
"
```

---

## Embedding Statistics

### Embeddings by Type

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    entity_type,
    COUNT(*) as count,
    COUNT(DISTINCT entity_id) as unique_entities
FROM embeddings
GROUP BY entity_type
ORDER BY entity_type;
"
```

**Output**:
```
entity_type      | count | unique_entities
-----------------+-------+-----------------
document_summary |     6 |               6
proposition      |    70 |              70
section          |    15 |              15
```

### Embeddings Coverage

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    'documents' as entity_type,
    COUNT(*) as total_entities,
    (SELECT COUNT(*) FROM embeddings WHERE entity_type = 'document_summary') as with_embedding,
    ROUND(100.0 * (SELECT COUNT(*) FROM embeddings WHERE entity_type = 'document_summary') / COUNT(*), 2) as coverage_pct
FROM documents
UNION ALL
SELECT
    'sections',
    COUNT(*),
    (SELECT COUNT(*) FROM embeddings WHERE entity_type = 'section'),
    ROUND(100.0 * (SELECT COUNT(*) FROM embeddings WHERE entity_type = 'section') / COUNT(*), 2)
FROM semantic_sections
UNION ALL
SELECT
    'propositions',
    COUNT(*),
    (SELECT COUNT(*) FROM embeddings WHERE entity_type = 'proposition'),
    ROUND(100.0 * (SELECT COUNT(*) FROM embeddings WHERE entity_type = 'proposition') / COUNT(*), 2)
FROM semantic_propositions;
"
```

**Output**:
```
entity_type  | total_entities | with_embedding | coverage_pct
-------------+----------------+----------------+--------------
documents    |              6 |              6 |       100.00
sections     |             15 |             15 |       100.00
propositions |             70 |             70 |       100.00
```

### Embedding Dimensions Check

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    entity_type,
    jsonb_array_length(embedding) as dimensions,
    COUNT(*) as count
FROM embeddings
GROUP BY entity_type, jsonb_array_length(embedding);
"
```

**Expected**: All should be 768 dimensions (text-embedding-004)

---

## Search & Query

### Search Documents by Title

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    id,
    title,
    mode,
    category
FROM documents
WHERE title ILIKE '%smart%contract%'
ORDER BY created_at DESC;
"
```

### Search Content

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    d.title,
    d.mode,
    LEFT(d.content, 100) as content_preview
FROM documents d
WHERE d.content ILIKE '%blockchain%'
LIMIT 10;
"
```

### Find Documents Without Chunks

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    d.id,
    d.title,
    d.mode,
    COUNT(s.id) as section_count
FROM documents d
LEFT JOIN semantic_sections s ON s.document_id = d.id
GROUP BY d.id, d.title, d.mode
HAVING COUNT(s.id) = 0;
"
```

**Expected**: Should return 0 rows (all documents should have chunks)

### Recent Activity

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    'document' as type,
    title as name,
    created_at,
    updated_at
FROM documents
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC
LIMIT 20;
"
```

---

## Real-time Monitoring

### Watch Database Changes (Auto-refresh every 2 seconds)

```bash
watch -n 2 'docker exec docker-db-1 psql -U postgres -d crawl4ai -t -c "
SELECT
    '\''Documents:'\'' as metric, COUNT(*)::text as count FROM documents
UNION ALL SELECT '\''Sections:'\'', COUNT(*)::text FROM semantic_sections
UNION ALL SELECT '\''Propositions:'\'', COUNT(*)::text FROM semantic_propositions
UNION ALL SELECT '\''Embeddings:'\'', COUNT(*)::text FROM embeddings;
"'
```

**Press Ctrl+C to stop**

### Watch Latest Documents

```bash
watch -n 5 'docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    title,
    mode,
    created_at
FROM documents
ORDER BY created_at DESC
LIMIT 5;
"'
```

### Monitor Database Size

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    pg_size_pretty(pg_database_size('crawl4ai')) as database_size,
    pg_size_pretty(pg_total_relation_size('documents')) as documents_size,
    pg_size_pretty(pg_total_relation_size('semantic_sections')) as sections_size,
    pg_size_pretty(pg_total_relation_size('semantic_propositions')) as propositions_size,
    pg_size_pretty(pg_total_relation_size('embeddings')) as embeddings_size;
"
```

---

## Performance Metrics

### Table Sizes

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY size_bytes DESC;
"
```

### Index Usage

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
"
```

### Query Statistics

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    relname as table_name,
    seq_scan as sequential_scans,
    idx_scan as index_scans,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY seq_scan DESC;
"
```

### Connection Info

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    COUNT(*) as total_connections,
    COUNT(*) FILTER (WHERE state = 'active') as active_connections,
    COUNT(*) FILTER (WHERE state = 'idle') as idle_connections
FROM pg_stat_activity
WHERE datname = 'crawl4ai';
"
```

---

## Troubleshooting

### Check for Orphaned Records

**Sections without documents**:
```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT s.id, s.document_id
FROM semantic_sections s
LEFT JOIN documents d ON s.document_id = d.id
WHERE d.id IS NULL;
"
```

**Propositions without sections**:
```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT p.id, p.section_id
FROM semantic_propositions p
LEFT JOIN semantic_sections s ON p.section_id = s.id
WHERE s.id IS NULL;
"
```

**Embeddings without entities**:
```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    e.entity_type,
    e.entity_id,
    CASE
        WHEN e.entity_type = 'document_summary' THEN (SELECT COUNT(*) FROM documents WHERE id = e.entity_id)
        WHEN e.entity_type = 'section' THEN (SELECT COUNT(*) FROM semantic_sections WHERE id = e.entity_id)
        WHEN e.entity_type = 'proposition' THEN (SELECT COUNT(*) FROM semantic_propositions WHERE id = e.entity_id)
    END as entity_exists
FROM embeddings e
HAVING entity_exists = 0;
"
```

**Expected**: All queries should return 0 rows

### Check Data Integrity

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
-- Check for NULL required fields
SELECT 'documents_with_null' as issue, COUNT(*) as count
FROM documents WHERE title IS NULL OR content IS NULL
UNION ALL
SELECT 'sections_with_null', COUNT(*)
FROM semantic_sections WHERE content IS NULL
UNION ALL
SELECT 'propositions_with_null', COUNT(*)
FROM semantic_propositions WHERE content IS NULL
UNION ALL
SELECT 'embeddings_with_null', COUNT(*)
FROM embeddings WHERE embedding IS NULL;
"
```

### Vacuum and Analyze

```bash
# Vacuum to reclaim space
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "VACUUM ANALYZE;"

# Get detailed statistics
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    schemaname,
    tablename,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'public';
"
```

---

## Useful Aliases

Add these to your `~/.bashrc` for quick access:

```bash
# Database status
alias db-status='docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    (SELECT COUNT(*) FROM documents) as docs,
    (SELECT COUNT(*) FROM semantic_sections) as sections,
    (SELECT COUNT(*) FROM semantic_propositions) as props,
    (SELECT COUNT(*) FROM embeddings) as embeddings;
"'

# List all documents
alias db-docs='docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT id, title, mode, created_at FROM documents ORDER BY created_at DESC;
"'

# Database size
alias db-size='docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT pg_size_pretty(pg_database_size('\''crawl4ai'\'')) as size;
"'

# Watch database (auto-refresh)
alias db-watch='watch -n 2 "docker exec docker-db-1 psql -U postgres -d crawl4ai -t -c \"
SELECT COUNT(*) FROM documents;
\""'

# Clear database
alias db-clear='docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
TRUNCATE TABLE documents CASCADE;
TRUNCATE TABLE embeddings;
"'
```

Then reload:
```bash
source ~/.bashrc
```

Usage:
```bash
db-status    # Quick status check
db-docs      # List all documents
db-size      # Database size
db-watch     # Watch in real-time
```

---

## Python Scripts

### Get Document Stats

Create `scripts/db_stats.py`:

```python
#!/usr/bin/env python3
"""Quick database statistics"""

import subprocess
import json

def get_stats():
    cmd = [
        "docker", "exec", "docker-db-1",
        "psql", "-U", "postgres", "-d", "crawl4ai",
        "-t", "-A", "-c",
        """
        SELECT
            (SELECT COUNT(*) FROM documents) as documents,
            (SELECT COUNT(*) FROM semantic_sections) as sections,
            (SELECT COUNT(*) FROM semantic_propositions) as propositions,
            (SELECT COUNT(*) FROM embeddings) as embeddings;
        """
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    docs, sections, props, embeddings = result.stdout.strip().split('|')

    print(f"📊 Database Statistics")
    print(f"{'='*50}")
    print(f"Documents:     {docs:>6}")
    print(f"Sections:      {sections:>6}")
    print(f"Propositions:  {props:>6}")
    print(f"Embeddings:    {embeddings:>6}")
    print(f"{'='*50}")

    # Calculate averages
    if int(docs) > 0:
        avg_sections = int(sections) / int(docs)
        avg_props = int(props) / int(docs)
        print(f"\nAverages per document:")
        print(f"Sections:      {avg_sections:>6.1f}")
        print(f"Propositions:  {avg_props:>6.1f}")

if __name__ == "__main__":
    get_stats()
```

Usage:
```bash
chmod +x scripts/db_stats.py
python3 scripts/db_stats.py
```

### Search Documents

Create `scripts/db_search.py`:

```python
#!/usr/bin/env python3
"""Search documents in database"""

import subprocess
import sys

def search_documents(query):
    cmd = [
        "docker", "exec", "docker-db-1",
        "psql", "-U", "postgres", "-d", "crawl4ai",
        "-c",
        f"""
        SELECT
            d.id,
            d.title,
            d.mode,
            LEFT(d.content, 100) as preview
        FROM documents d
        WHERE
            d.title ILIKE '%{query}%' OR
            d.content ILIKE '%{query}%'
        ORDER BY d.created_at DESC;
        """
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 db_search.py <query>")
        sys.exit(1)

    search_documents(sys.argv[1])
```

Usage:
```bash
python3 scripts/db_search.py "blockchain"
python3 scripts/db_search.py "smart contract"
```

---

## Dashboard View

### Complete Overview

```bash
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
-- HEADER
SELECT '════════════════════════════════════════════════' as line
UNION ALL SELECT '           DATABASE DASHBOARD              '
UNION ALL SELECT '════════════════════════════════════════════'
UNION ALL SELECT ''
UNION ALL SELECT '📊 SUMMARY'
UNION ALL SELECT '────────────────────────────────────────────'
UNION ALL SELECT 'Documents:     ' || COUNT(*)::text FROM documents
UNION ALL SELECT 'Sections:      ' || COUNT(*)::text FROM semantic_sections
UNION ALL SELECT 'Propositions:  ' || COUNT(*)::text FROM semantic_propositions
UNION ALL SELECT 'Embeddings:    ' || COUNT(*)::text FROM embeddings
UNION ALL SELECT ''
UNION ALL SELECT '📄 BY MODE'
UNION ALL SELECT '────────────────────────────────────────────';

SELECT
    RPAD(mode::text, 15) || ': ' || COUNT(*)::text as distribution
FROM documents
GROUP BY mode;

SELECT '════════════════════════════════════════════════' as line;
"
```

---

## Summary

### Quick Commands Reference

```bash
# Status check
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "SELECT COUNT(*) FROM documents;"

# List documents
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "SELECT id, title, mode FROM documents;"

# Watch in real-time
watch -n 2 'docker exec docker-db-1 psql -U postgres -d crawl4ai -t -c "SELECT COUNT(*) FROM documents;"'

# Database size
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "SELECT pg_size_pretty(pg_database_size('crawl4ai'));"

# Clear all data
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "TRUNCATE TABLE documents CASCADE; TRUNCATE TABLE embeddings;"
```

---

**Your database monitoring toolkit is ready!** 📊

Use these commands to watch your RAG system grow and maintain data quality! 🚀
