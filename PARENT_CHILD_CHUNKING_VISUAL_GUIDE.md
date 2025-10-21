# Parent-Child Chunking - Visual Guide

**Based on Dify.ai RAG Strategy**

---

## 1. Document Structure Comparison

### Traditional Chunking (What We Have Now)
```
┌─────────────────────────────────────────────────────────────┐
│  DOCUMENT: "EOS Network Guide"                              │
├─────────────────────────────────────────────────────────────┤
│  ## Introduction                                            │
│  The EOS Network is a blockchain platform. It provides      │
│  smart contract capabilities. Developers can build apps.    │
│                                                              │
│  ## Getting Started                                         │
│  First, install the CLI tool. Then create a new project.    │
│  The CLI will generate boilerplate code.                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
            ┌─────────────────────────┐
            │  Fixed-size chunking    │
            └─────────────────────────┘
                          ↓
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Chunk 1         │  │  Chunk 2         │  │  Chunk 3         │
│  (200 tokens)    │  │  (200 tokens)    │  │  (200 tokens)    │
│  ✅ Embedded     │  │  ✅ Embedded     │  │  ✅ Embedded     │
│  ✅ Searched     │  │  ✅ Searched     │  │  ✅ Searched     │
│  ✅ Returned     │  │  ✅ Returned     │  │  ✅ Returned     │
└──────────────────┘  └──────────────────┘  └──────────────────┘

Problem: May break sentences mid-context, lose document structure
```

### Parent-Child Chunking (Dify.ai Approach)
```
┌─────────────────────────────────────────────────────────────┐
│  DOCUMENT: "EOS Network Guide"                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
            ┌─────────────────────────┐
            │  Split by headers (##)  │
            └─────────────────────────┘
                          ↓
        ┌────────────────────┬────────────────────┐
        ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ PARENT CHUNK 1  │  │ PARENT CHUNK 2  │  │ PARENT CHUNK 3  │
│ (Paragraph)     │  │ (Paragraph)     │  │ (Paragraph)     │
│ ❌ NOT embedded │  │ ❌ NOT embedded │  │ ❌ NOT embedded │
│ ❌ NOT searched │  │ ❌ NOT searched │  │ ❌ NOT searched │
│ ✅ RETURNED     │  │ ✅ RETURNED     │  │ ✅ RETURNED     │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
    Split by "."         Split by "."         Split by "."
         ▼                    ▼                    ▼
  ┌───────────┐        ┌───────────┐        ┌───────────┐
  │ Child 1.1 │        │ Child 2.1 │        │ Child 3.1 │
  │ ✅ Embed  │        │ ✅ Embed  │        │ ✅ Embed  │
  │ ✅ Search │        │ ✅ Search │        │ ✅ Search │
  ├───────────┤        ├───────────┤        ├───────────┤
  │ Child 1.2 │        │ Child 2.2 │        │ Child 3.2 │
  │ ✅ Embed  │        │ ✅ Embed  │        │ ✅ Embed  │
  │ ✅ Search │        │ ✅ Search │        │ ✅ Search │
  ├───────────┤        ├───────────┤        ├───────────┤
  │ Child 1.3 │        │ Child 2.3 │        │ Child 3.3 │
  │ ✅ Embed  │        │ ✅ Embed  │        │ ✅ Embed  │
  │ ✅ Search │        │ ✅ Search │        │ ✅ Search │
  └───────────┘        └───────────┘        └───────────┘

Advantage: Precise search via children, full context via parents
```

---

## 2. Two Modes Side-by-Side

### Mode 1: Paragraph Mode (Your Requirement)
```
INPUT DOCUMENT:
┌─────────────────────────────────────────────────────────────┐
│  # EOS Network Guide                                        │
│                                                              │
│  ## Introduction to EOS                                     │
│  The EOS Network is a blockchain platform. It provides      │
│  smart contract capabilities. Developers can build dApps.   │
│                                                              │
│  ## CLI Installation                                        │
│  First, install the CLI tool using npm. Then create a new   │
│  project. The CLI generates boilerplate code.               │
└─────────────────────────────────────────────────────────────┘

PARENT CHUNKS (split by "##"):
┌─────────────────────────────────────────────────────────────┐
│ PARENT 1: Introduction to EOS                               │
├─────────────────────────────────────────────────────────────┤
│  The EOS Network is a blockchain platform. It provides      │
│  smart contract capabilities. Developers can build dApps.   │
│                                                              │
│  Metadata: {section: "Introduction to EOS"}                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PARENT 2: CLI Installation                                  │
├─────────────────────────────────────────────────────────────┤
│  First, install the CLI tool using npm. Then create a new   │
│  project. The CLI generates boilerplate code.               │
│                                                              │
│  Metadata: {section: "CLI Installation"}                    │
└─────────────────────────────────────────────────────────────┘

CHILD CHUNKS (split by "."):
From PARENT 1:
  └─ Child 1.1: "The EOS Network is a blockchain platform"
  └─ Child 1.2: "It provides smart contract capabilities"
  └─ Child 1.3: "Developers can build dApps"

From PARENT 2:
  └─ Child 2.1: "First, install the CLI tool using npm"
  └─ Child 2.2: "Then create a new project"
  └─ Child 2.3: "The CLI generates boilerplate code"

EMBEDDINGS:
  ✅ Child 1.1 → [0.123, -0.456, ...]
  ✅ Child 1.2 → [0.789, -0.234, ...]
  ✅ Child 1.3 → [0.345, -0.678, ...]
  ✅ Child 2.1 → [0.901, -0.012, ...]
  ✅ Child 2.2 → [0.567, -0.890, ...]
  ✅ Child 2.3 → [0.234, -0.567, ...]

  ❌ Parent 1 → NOT embedded (stored as text)
  ❌ Parent 2 → NOT embedded (stored as text)
```

### Mode 2: Full Doc Mode (Your Requirement)
```
INPUT DOCUMENT:
┌─────────────────────────────────────────────────────────────┐
│  # EOS Network Guide                                        │
│                                                              │
│  The EOS Network is a blockchain platform. It provides      │
│  smart contract capabilities. CLI installation is easy.     │
│  Developers can build powerful dApps.                       │
└─────────────────────────────────────────────────────────────┘

PARENT CHUNK (entire document):
┌─────────────────────────────────────────────────────────────┐
│ PARENT: [ENTIRE DOCUMENT]                                   │
├─────────────────────────────────────────────────────────────┤
│  # EOS Network Guide                                        │
│                                                              │
│  The EOS Network is a blockchain platform. It provides      │
│  smart contract capabilities. CLI installation is easy.     │
│  Developers can build powerful dApps.                       │
│                                                              │
│  Metadata: {document_id: "eos_guide", type: "full_doc"}     │
└─────────────────────────────────────────────────────────────┘

CHILD CHUNKS (split by "."):
From PARENT (document):
  └─ Child 1: "The EOS Network is a blockchain platform"
  └─ Child 2: "It provides smart contract capabilities"
  └─ Child 3: "CLI installation is easy"
  └─ Child 4: "Developers can build powerful dApps"

EMBEDDINGS:
  ✅ Child 1 → [0.123, -0.456, ...]
  ✅ Child 2 → [0.789, -0.234, ...]
  ✅ Child 3 → [0.345, -0.678, ...]
  ✅ Child 4 → [0.901, -0.012, ...]

  ❌ Parent → NOT embedded (entire document stored as text)
```

---

## 3. Retrieval Process Flow

```
USER QUERY: "How do I install the EOS CLI?"
│
│ Step 1: Generate query embedding
├─► Query Embedding: [0.912, -0.034, 0.567, ...]
│
│ Step 2: Search child chunk embeddings
├─► Vector similarity search (cosine)
│
│   Results (Top 5 child chunks):
│   ┌─────────────────────────────────────────────────────┐
│   │ 1. Child 2.1: "First, install the CLI tool..."     │
│   │    Similarity: 0.89  ⭐ BEST MATCH                 │
│   │    Parent: PARENT 2 (CLI Installation)             │
│   ├─────────────────────────────────────────────────────┤
│   │ 2. Child 2.2: "Then create a new project"          │
│   │    Similarity: 0.76                                 │
│   │    Parent: PARENT 2 (CLI Installation)             │
│   ├─────────────────────────────────────────────────────┤
│   │ 3. Child 1.1: "The EOS Network is..."              │
│   │    Similarity: 0.65                                 │
│   │    Parent: PARENT 1 (Introduction)                 │
│   └─────────────────────────────────────────────────────┘
│
│ Step 3: Retrieve parent chunks
├─► Get unique parents from matched children
│   • PARENT 2 (from Child 2.1, 2.2)
│   • PARENT 1 (from Child 1.1)
│
│ Step 4: Send to LLM
└─► Context for LLM:
    ┌───────────────────────────────────────────────────┐
    │ PARENT 2 (Full paragraph):                        │
    │ "First, install the CLI tool using npm. Then      │
    │ create a new project. The CLI generates           │
    │ boilerplate code."                                │
    ├───────────────────────────────────────────────────┤
    │ PARENT 1 (Full paragraph):                        │
    │ "The EOS Network is a blockchain platform. It     │
    │ provides smart contract capabilities..."          │
    └───────────────────────────────────────────────────┘

LLM Response: "To install the EOS CLI, you need to use npm.
First, run the installation command, then you can create a
new project which will generate boilerplate code for you..."
```

---

## 4. Storage Efficiency Comparison

### Traditional Approach (Embed Everything)
```
Document: 1000 words → 5 chunks (200 words each)

Embeddings Generated: 5
Storage: 5 × 768 floats = 3,840 floats

Cost:
  • Embedding API calls: 5
  • Vector storage: 3,840 floats
  • Search operations: Check all 5 embeddings
```

### Parent-Child Approach (Embed Children Only)
```
Document: 1000 words
  ↓
Parent chunks: 2 paragraphs (500 words each)
  ↓
Child chunks: 10 sentences (100 words each)

Embeddings Generated: 10 (child chunks only)
Storage:
  • Vector: 10 × 768 floats = 7,680 floats
  • Text: 2 parent chunks (no embeddings)

Cost:
  • Embedding API calls: 10 (but more precise)
  • Vector storage: 7,680 floats
  • Search operations: Check 10 embeddings
  • Context returned: FULL paragraphs (not fragments)

Advantage:
  ✅ More precise matching (sentence-level)
  ✅ Better context (paragraph-level)
  ✅ Reasonable cost increase for better quality
```

---

## 5. Database Schema for Implementation

### Parent Chunks Table
```sql
CREATE TABLE parent_chunks (
    id                TEXT PRIMARY KEY,
    document_id       TEXT REFERENCES documents(id),
    mode              TEXT,           -- 'paragraph' or 'full_doc'
    content           TEXT NOT NULL,  -- Full paragraph or document
    chunk_index       INT,            -- Order in document
    header            TEXT,           -- Section header (if paragraph mode)
    metadata          JSONB,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example row:
{
    "id": "para_eos_intro_001",
    "document_id": "eos_network_smart_contract_development_paragraph",
    "mode": "paragraph",
    "content": "## Introduction\n\nThe EOS Network is...",
    "chunk_index": 1,
    "header": "Introduction",
    "metadata": {"section": "intro", "word_count": 45}
}
```

### Child Chunks Table
```sql
CREATE TABLE child_chunks (
    id                TEXT PRIMARY KEY,
    parent_chunk_id   TEXT REFERENCES parent_chunks(id),
    content           TEXT NOT NULL,  -- Single sentence
    embedding         vector(768),    -- Vector embedding
    chunk_index       INT,            -- Order within parent
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HNSW Index for fast similarity search
CREATE INDEX idx_child_chunk_embeddings
ON child_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Example row:
{
    "id": "child_eos_intro_001_01",
    "parent_chunk_id": "para_eos_intro_001",
    "content": "The EOS Network is a blockchain platform.",
    "embedding": [0.123, -0.456, 0.789, ...],
    "chunk_index": 1
}
```

### Query Example
```sql
-- Search: Find child chunks similar to query
SELECT c.id, c.content, c.embedding <=> $query_embedding AS similarity,
       p.id as parent_id, p.content as parent_content
FROM child_chunks c
JOIN parent_chunks p ON c.parent_chunk_id = p.id
WHERE c.embedding <=> $query_embedding < 0.5  -- Similarity threshold
ORDER BY c.embedding <=> $query_embedding
LIMIT 5;

-- Result:
-- Returns child chunks + their parent chunks for context
```

---

## 6. Your Implementation Requirements

Based on your specifications:

### Paragraph Mode
```yaml
Parent Chunks:
  delimiter: "##"           # Markdown headers
  mode: "paragraph"
  example: "## Introduction" → one parent chunk

Child Chunks:
  delimiter: "."            # Sentence boundary
  derived_from: "parent_chunk"
  example: "The EOS Network is a blockchain." → one child chunk

Embeddings:
  target: "child_chunks_only"
  model: "text-embedding-004"
  dimensions: 768

Retrieval:
  search: "child_chunk_embeddings"
  return: "parent_chunk_content"
```

### Full Doc Mode
```yaml
Parent Chunks:
  scope: "entire_document"
  mode: "full_doc"
  max_tokens: 10000

Child Chunks:
  delimiter: "."            # Same as paragraph mode
  derived_from: "document"
  example: "The EOS Network is a blockchain." → one child chunk

Embeddings:
  target: "child_chunks_only"
  model: "text-embedding-004"
  dimensions: 768

Retrieval:
  search: "child_chunk_embeddings"
  return: "parent_chunk_content (entire document)"
```

---

## Summary

### Key Takeaways

1. **Only child chunks are embedded** ✅
   - Reduces cost
   - Increases precision
   - Speeds up search

2. **Parent chunks provide context** ✅
   - Not embedded
   - Retrieved via parent-child relationship
   - Sent directly to LLM

3. **Two-stage retrieval** ✅
   - Stage 1: Search child embeddings
   - Stage 2: Return parent chunks

4. **Your configuration** ✅
   - Paragraph mode: Split by `##`, children by `.`
   - Full doc mode: Entire doc as parent, children by `.`
   - Only child chunks embedded

---

**Ready to implement?** ✅

Next steps:
1. Create `hybrid_chunker.py`
2. Update PostgreSQL schema (add parent/child tables)
3. Update document creator to generate chunks
4. Update search to use child→parent retrieval
