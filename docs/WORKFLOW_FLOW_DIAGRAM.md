# Workflow Data Flow - Complete & Verified

**Date**: 2025-10-26
**Status**: ✅ **ALL FLOWS VERIFIED**

---

## Complete Workflow Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WORKFLOW EXECUTION                          │
└─────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │   START URL  │
    └──────┬───────┘
           │
           ▼
    ┌──────────────────────┐
    │   1. CRAWL NODE      │
    │   (BFS Crawler)      │
    └──────┬───────────────┘
           │
           │ crawl_result = {
           │   'crawl_data': {url: {markdown, ...}},
           │   'pages_crawled': int,
           │   'links_discovered': int,
           │   'output_dir': str
           │ }
           │
           ▼
    ┌──────────────────────┐
    │  2. EXTRACT TOPICS   │
    │  (LLM-based)         │
    └──────┬───────────────┘
           │
           │ extract_result = {
           │   'all_topics': {url: [topics]},
           │   'total_topics': int,
           │   'urls_processed': int
           │ }
           │
           │ Topic = {
           │   'title': str,
           │   'content': str,
           │   'category': str,
           │   'keywords': [str],
           │   'source_urls': [str]
           │ }
           │
           ▼
    ┌──────────────────────┐
    │ 3. MERGE DECISION    │
    │ (Embeddings + LLM)   │
    └──────┬───────────────┘
           │
           │ merge_result = {
           │   'results': {
           │     'merge': [{'topic': {...}, 'decision': {...}}],
           │     'create': [{'topic': {...}, 'decision': {...}}],
           │     'verify': [{'topic': {...}, 'decision': {...}}]
           │   },
           │   'merge_count': int,
           │   'create_count': int,
           │   'verify_count': int
           │ }
           │
           ├─────────────────┬─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────┐    ┌──────────┐      ┌──────────┐
    │  MERGE   │    │  CREATE  │      │  VERIFY  │
    │  Topics  │    │  Topics  │      │  Topics  │
    └────┬─────┘    └────┬─────┘      └────┬─────┘
         │               │                   │
         │               └───────┬───────────┘
         │                       │
         ▼                       ▼
    ┌──────────────────┐  ┌──────────────────┐
    │ 5. MERGER NODE   │  │ 4. CREATOR NODE  │
    └──────┬───────────┘  └──────┬───────────┘
           │                     │
           │                     ▼
           │              ┌──────────────────┐
           │              │  NEW DOCUMENTS   │
           │              │  + Chunks        │
           │              │  + Embeddings    │
           │              └──────┬───────────┘
           │                     │
           └──────────┬──────────┘
                      │
                      ▼
              ┌──────────────────┐
              │   PostgreSQL DB  │
              │   + pgvector     │
              └──────────────────┘
```

---

## Node Details

### 1. CrawlNode (BFS Crawler)

**Purpose**: Crawl web pages using breadth-first search

**Input**:
- `start_url`: Starting URL
- `max_pages`: Maximum pages to crawl
- `same_domain_only`: Limit to same domain

**Output**:
```python
{
    'crawl_data': {
        'url1': {'success': True, 'markdown': '...', 'links_found': [...], ...},
        'url2': {'success': True, 'markdown': '...', 'links_found': [...], ...}
    },
    'pages_crawled': 10,
    'links_discovered': 45,
    'output_dir': 'bfs_crawled'
}
```

**Key Features**:
- BFS traversal ensures breadth-first coverage
- Markdown extraction from HTML
- Link discovery and queuing
- Same-domain filtering option

---

### 2. ExtractTopicsNode (LLM Topic Extraction)

**Purpose**: Extract structured topics from crawled content using LLM

**Input**: `crawl_result` from CrawlNode

**Process**:
1. For each crawled page with markdown content
2. Send to Gemini LLM for topic extraction
3. LLM identifies distinct topics in the content
4. Each topic gets title, content, category, keywords

**Output**:
```python
{
    'all_topics': {
        'url1': [
            {
                'title': 'EOS Network Staking',
                'content': 'Detailed explanation...',
                'category': 'concept',
                'keywords': ['staking', 'eos', 'blockchain'],
                'source_urls': ['url1']
            },
            # ... more topics from url1
        ],
        'url2': [...]
    },
    'total_topics': 25,
    'urls_processed': 10
}
```

**Key Features**:
- LLM-powered intelligent topic segmentation
- Automatic categorization (concept, tutorial, guide, reference)
- Keyword extraction
- Source URL tracking

---

### 3. MergeDecisionNode (Embedding-based Decision)

**Purpose**: Decide whether each topic should merge with existing docs or create new

**Input**:
- `extract_result` from ExtractTopicsNode
- `existing_documents` from database

**Process**:
1. For each extracted topic:
   - Create embedding for topic content
   - Compare with embeddings of existing documents
   - Calculate cosine similarity
2. Make decision based on thresholds:
   - `similarity >= 0.85` → **MERGE** (high confidence)
   - `similarity <= 0.4` → **CREATE** (distinct topic)
   - `0.4 < similarity < 0.85` → **VERIFY** (LLM decides)

**Output**:
```python
{
    'results': {
        'merge': [
            {
                'topic': {title, content, category, keywords, ...},
                'decision': {
                    'action': 'merge',
                    'target_doc_id': 'doc_123',        # ← ID of existing doc
                    'target_doc_title': 'EOS Staking',
                    'similarity': 0.92,
                    'reason': 'High similarity...',
                    'confidence': 'high'
                }
            }
        ],
        'create': [
            {
                'topic': {title, content, ...},
                'decision': {
                    'action': 'create',
                    'similarity': 0.25,
                    'reason': 'Low similarity...',
                    'confidence': 'high'
                }
            }
        ],
        'verify': [
            {
                'topic': {title, content, ...},
                'decision': {
                    'action': 'create',  # LLM decided
                    'similarity': 0.65,
                    'reason': 'LLM recommended...',
                    'confidence': 'medium',
                    'llm_used': True
                }
            }
        ]
    },
    'merge_count': 5,
    'create_count': 15,
    'verify_count': 3
}
```

**Key Features**:
- Embedding-based similarity (Gemini text-embedding-004)
- Three-way classification (merge/create/verify)
- Optional LLM verification for uncertain cases
- Prevents document duplication

---

### 4. DocumentCreatorNode (Create New Documents)

**Purpose**: Create new documents from topics classified as 'create' or 'verify'

**Input**: `merge_result` from MergeDecisionNode

**Process**:
1. Extract topics from `merge_result['results']['create']`
2. Also extract from `merge_result['results']['verify']` (fallback)
3. For each topic:
   - Generate document ID from title
   - Use SimpleQualityChunker to split content
   - Create embeddings for each chunk
   - Format as database record
4. Batch insert to PostgreSQL

**Key Logic**:
```python
# Extract create topics
create_topics = [item['topic'] for item in results['create']]

# Add verify topics (LLM-uncertain cases)
verify_topics = results.get('verify', [])
if verify_topics:
    create_topics.extend([item['topic'] for item in verify_topics])

# Create documents
doc_results = creator.create_documents_batch(create_topics)

# Save to database
db.insert_documents_batch(doc_results['documents'])
```

**Output**:
```python
{
    'doc_results': {
        'documents': [
            {
                'id': 'eos_staking_overview_20251026',
                'title': 'EOS Staking Overview',
                'content': '...',
                'summary': '...',
                'category': 'concept',
                'keywords': ['staking', 'eos'],
                'chunks': [
                    {'id': '...', 'content': '...', 'chunk_index': 0, 'token_count': 300},
                    {'id': '...', 'content': '...', 'chunk_index': 1, 'token_count': 250}
                ]
            }
        ]
    },
    'total_topics': 18,
    'documents_created': 18
}
```

**Key Features**:
- SimpleQualityChunker for consistent chunking (200-400 tokens)
- 50-token overlap between chunks
- Batch processing for efficiency
- PostgreSQL storage with pgvector

---

### 5. DocumentMergerNode (Merge with Existing Documents)

**Purpose**: Merge topics into existing documents and re-chunk

**Input**:
- `merge_result` from MergeDecisionNode
- `existing_documents` from database

**Process**:
1. Extract merge items from `merge_result['results']['merge']`
2. For each merge item:
   - Get `target_doc_id` from decision
   - Look up existing document by ID in `existing_documents`
   - Create merge pair: `{topic, existing_document}`
3. Use LLM to intelligently merge topic content with existing content
4. Re-chunk merged content (SimpleQualityChunker)
5. Update database with merged document

**Key Logic**:
```python
# Step 1: Collect merge topics with target IDs
merge_topics = []
for item in results['merge']:
    merge_topics.append({
        'topic': item['topic'],
        'target_doc_id': item['decision']['target_doc_id']  # ← Key field
    })

# Step 2: Look up existing documents and create merge pairs
merge_pairs = []
for mt in merge_topics:
    target_doc_id = mt['target_doc_id']
    if target_doc_id and existing_documents:
        # Find document by ID
        target_doc = next(
            (doc for doc in existing_documents if doc['id'] == target_doc_id),
            None
        )
        if target_doc:
            merge_pairs.append({
                'topic': mt['topic'],
                'existing_document': target_doc
            })

# Step 3: Merge documents
merge_results = merger.merge_documents_batch(merge_pairs)

# Step 4: Save merged documents
merger.save_merged_documents(merge_results, save_to_db=True)
```

**Output**:
```python
{
    'merge_results': {
        'merged_documents': [...]
    },
    'total_topics': 5,
    'documents_merged': 5
}
```

**Key Features**:
- LLM-powered intelligent content merging
- Preserves document structure and metadata
- Re-chunks after merging for consistent chunk sizes
- Updates database atomically

---

## Critical Data Structure Mappings

### Decision Field Mapping (FIXED)
```python
# MergeDecisionNode returns:
'decision': {
    'target_doc_id': 'doc_123'  # ← Correct field name
}

# DocumentMergerNode accesses:
target_doc_id = item['decision']['target_doc_id']  # ← Fixed

# OLD (WRONG):
# target_document = item['decision']['target_document']  # ❌ This field doesn't exist
```

### Document Lookup (FIXED)
```python
# DocumentMergerNode looks up document:
target_doc = next(
    (doc for doc in existing_documents if doc['id'] == target_doc_id),
    None
)

# OLD (WRONG):
# target_doc = mt['target_document']  # ❌ Assumed full doc was passed
```

---

## Flow Validation Results

| Check | Status | Notes |
|-------|--------|-------|
| CrawlNode → ExtractTopicsNode | ✅ Pass | crawl_result structure matches |
| ExtractTopicsNode → MergeDecisionNode | ✅ Pass | extract_result structure matches |
| MergeDecisionNode → DocumentCreatorNode | ✅ Pass | results['create'] exists |
| MergeDecisionNode → DocumentMergerNode | ✅ Pass | results['merge'] exists |
| Field name consistency | ✅ Pass | target_doc_id (not target_document) |
| Document lookup logic | ✅ Pass | Looks up by ID in existing_documents |
| Verify topic handling | ✅ Pass | Creator handles verify fallback |

---

## Execution Flow Example

### Scenario: Crawling EOS Documentation

1. **Crawl** 10 pages from docs.eosnetwork.com
   - Output: 10 markdown documents

2. **Extract** topics from markdown
   - Output: 25 topics (multiple topics per page)

3. **Decide** merge vs create
   - Existing DB has 5 documents
   - Results:
     - 8 topics → MERGE (high similarity with existing)
     - 15 topics → CREATE (distinct new topics)
     - 2 topics → VERIFY (uncertain, LLM decides)

4. **Create** new documents
   - Creates 17 documents (15 create + 2 verify)
   - Each document chunked into 1-3 chunks
   - Saves to PostgreSQL

5. **Merge** with existing
   - Merges 8 topics into 5 existing documents
   - LLM intelligently combines content
   - Re-chunks merged documents
   - Updates PostgreSQL

**Final Result**: 22 documents total (5 merged + 17 new)

---

## Error Prevention

### Common Pitfalls (NOW FIXED)

1. ❌ **Wrong field name**: `target_document` instead of `target_doc_id`
   - ✅ Fixed: Uses correct `target_doc_id`

2. ❌ **Assumed full doc passed**: Expected document object instead of ID
   - ✅ Fixed: Looks up document by ID

3. ❌ **Missing existing_documents**: Merge without document list
   - ✅ Fixed: Checks `existing_documents` is provided

---

## Summary

✅ **Complete 5-node pipeline verified**
✅ **All data structures match**
✅ **Field names consistent**
✅ **Document lookup logic correct**
✅ **No structural mismatches**

**Status**: Production-ready for end-to-end execution
