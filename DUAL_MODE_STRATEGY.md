# Dual-Mode Strategy

**Date**: 2025-10-19
**Status**: ✅ Implemented

---

## 🎯 What is Dual-Mode?

Instead of choosing ONE formatting mode based on content size, we now **generate BOTH modes** for every document:

```
Old approach: 1 page → 1 mode (full_doc OR paragraph)
New approach: 1 page → 2 modes (full_doc AND paragraph)
```

---

## 💡 Why Dual-Mode?

### 1. **Maximum RAG Flexibility**
The retrieval system can choose the best format for each query:
- Simple question → Use `full_doc` version (whole context)
- Complex question → Use `paragraph` version (specific sections)
- Need overview → `full_doc`
- Need details → `paragraph` sections

### 2. **No Upfront Decision Needed**
- Don't need to guess which mode works best
- Let retrieval decide dynamically
- Can experiment with different strategies

### 3. **Minimal Cost (with Gemini)**
```
Example: 100 pages
- Old: 100 documents × 500 tokens = 50K tokens = $0.00125
- New: 200 documents × 500 tokens = 100K tokens = $0.00250
- Difference: < 1 cent for 100 pages!
```

### 4. **Better Quality**
- Always have full context available
- Always have sectioned version for granular search
- Can rank both and pick best match

---

## 🏗️ How It Works

### For Each Document:

```python
# System creates TWO versions:

# 1. Full-doc mode (flat structure)
full_doc = """
# Security - Complete Guide
Strong passwords should be at least 12 characters long. Use a mix of
uppercase, lowercase, numbers and symbols. Enable 2FA on all accounts.
Use authenticator apps instead of SMS.
"""

# 2. Paragraph mode (hierarchical)
paragraph = """
# Security - Complete Guide
## Password Security
Strong passwords should be at least 12 characters long. Use a mix of
uppercase, lowercase, numbers and symbols.
## Two-Factor Authentication
Enable 2FA on all accounts. Use authenticator apps instead of SMS.
"""
```

Both stored in database with different `mode` field values.

---

## 📊 Example

### Input:
```python
topics = [
    {'title': 'Password Security', 'category': 'security', 'content': '...'},
    {'title': '2FA Setup', 'category': 'security', 'content': '...'},
    {'title': 'Wallet Backup', 'category': 'wallet', 'content': '...'}
]
```

### Output (Dual-Mode):
```
4 documents created:
1. "Security - Complete Guide" (mode: full_doc)
2. "Security - Complete Guide" (mode: paragraph)
3. "Wallet - Complete Guide" (mode: full_doc)
4. "Wallet - Complete Guide" (mode: paragraph)
```

**Result**: 2 unique documents × 2 modes = 4 total documents

---

## 🔍 RAG Retrieval Examples

### Strategy 1: Search Both, Pick Best
```python
# Search both modes
results = search(query, modes=['full_doc', 'paragraph'])
best = max(results, key=lambda x: x['similarity'])
```

### Strategy 2: Mode-Specific
```python
# Simple query → full context
if is_simple_query(query):
    results = search(query, mode='full_doc', limit=1)

# Complex query → specific sections
else:
    results = search(query, mode='paragraph', limit=5)
```

### Strategy 3: Hybrid
```python
# Get context from full_doc
context = search(query, mode='full_doc', limit=1)

# Get details from paragraph sections
details = search(query, mode='paragraph', limit=3)

# Combine both
return combine(context, details)
```

### Strategy 4: Filter by Mode in SQL
```sql
-- Get only full_doc versions for overview
SELECT * FROM documents
WHERE mode = 'full_doc'
AND 1 - (embedding <=> $1) > 0.7
ORDER BY embedding <=> $1
LIMIT 3;

-- Get paragraph sections for details
SELECT * FROM documents
WHERE mode = 'paragraph'
AND category = 'security'
AND 1 - (embedding <=> $1) > 0.6
ORDER BY embedding <=> $1
LIMIT 5;
```

---

## 📝 Database Schema

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    topic_title VARCHAR(500),
    content TEXT,
    embedding vector(768),
    category VARCHAR(100),
    mode VARCHAR(20),  -- 'full_doc' or 'paragraph'
    ...
);

-- Index for efficient mode filtering
CREATE INDEX idx_documents_mode ON documents(mode);
```

---

## 💻 Code Usage

### Using Dual-Mode (New):

```python
from core.page_processor import PageProcessor

# Initialize processor
processor = PageProcessor()

# Process page - automatically creates BOTH modes
result = processor.process_page(topics, source_url)

print(f"Created {result['documents_created']} documents")
# Output: "Created 4 documents" (2 groups × 2 modes)
```

### Direct Merger Usage:

```python
from core.document_merger import DocumentMerger

merger = DocumentMerger()

# Create dual-mode documents
documents = merger.merge_topics_dual_mode(topics)

# Each unique document appears twice with different modes
for doc in documents:
    print(f"{doc['title']} - Mode: {doc['mode']}")
```

### Format Single Topic in Both Modes:

```python
from core.natural_formatter import NaturalFormatter

formatter = NaturalFormatter()

# Get both versions
full_doc, paragraph = formatter.format_topic_dual_mode(topic)

print(f"Full-doc has ## sections: {'##' in full_doc}")  # False
print(f"Paragraph has ## sections: {'##' in paragraph}")  # True
```

---

## 📈 Statistics

### Before (Single Mode):
- 3 topics → 2 documents
- Mode distribution: `{'full_doc': 1, 'paragraph': 1}`
- Cost: $0.00125 per 100 pages

### After (Dual Mode):
- 3 topics → 4 documents (2 unique × 2 modes)
- Mode distribution: `{'full_doc': 2, 'paragraph': 2}`
- Cost: $0.00250 per 100 pages
- **Extra cost**: < 1 cent per 100 pages!

---

## ✅ Benefits Summary

| Aspect | Single Mode | Dual Mode |
|--------|-------------|-----------|
| **Flexibility** | Limited | Maximum |
| **Storage** | 1x | 2x (negligible) |
| **Embeddings** | 1x | 2x |
| **Cost** | $0.00125 | $0.00250 (+$0.00125) |
| **RAG Options** | 1 format | 2 formats |
| **Quality** | Good | Better (more options) |

---

## 🚀 Migration

### For New Projects:
```bash
# Just use it - dual-mode is now the default
python test_dual_mode.py  # Verify it works
```

### For Existing Databases:
```bash
# Add mode column to existing database
chmod +x add_mode_column.sh
./add_mode_column.sh

# Existing documents will have mode=NULL (still work fine)
# New documents will have mode='full_doc' or 'paragraph'
```

---

## 🧪 Testing

### Run Dual-Mode Test:
```bash
python test_dual_mode.py
```

**Expected Output:**
```
✅ Input: 3 topics
✅ Output: 4 documents (dual-mode)
✅ Each unique document created in 2 modes
✅ Full-doc: Flat structure (no ## sections)
✅ Paragraph: Hierarchical structure (with ## sections)

🎉 Dual-mode strategy is working correctly!
```

---

## 🎯 Use Cases

### Use Case 1: Question Answering
- **Simple**: "What is 2FA?" → Use `full_doc` (complete context)
- **Complex**: "How to setup 2FA on multiple devices?" → Use `paragraph` (specific section)

### Use Case 2: Document Summarization
- Use `full_doc` versions for complete summaries
- Use `paragraph` versions to extract specific topics

### Use Case 3: Citation/Source Tracking
- Use `paragraph` mode to cite specific sections
- Use `full_doc` mode for general references

### Use Case 4: A/B Testing
- Test which mode performs better for your queries
- Switch dynamically based on results
- No need to regenerate embeddings!

---

## 🔧 Configuration

Currently, dual-mode is always ON by default. If you want single-mode:

```python
# Use the old method (single mode)
documents = merger.merge_topics(topics)  # Old way

# Use the new method (dual mode)
documents = merger.merge_topics_dual_mode(topics)  # New way (default)
```

---

## 📊 Cost Analysis

### Real-World Example: 1000 Pages

**Scenario**: Blog with 1000 pages, avg 500 tokens each

**Single Mode**:
- Documents: 1000
- Tokens: 500K
- Cost: $0.0125 (1.25 cents)

**Dual Mode**:
- Documents: 2000 (1000 × 2)
- Tokens: 1M
- Cost: $0.0250 (2.5 cents)
- **Extra**: $0.0125 (1.25 cents)

**Worth it?** Absolutely!
- 2x retrieval flexibility
- Better RAG performance
- Only 1.25 cents extra

---

## 🎉 Summary

**Dual-mode strategy gives you**:
- ✅ 2x retrieval options for same content
- ✅ Minimal extra cost with Gemini
- ✅ No upfront mode decisions needed
- ✅ Maximum RAG flexibility
- ✅ Better search quality

**Perfect for**: Any RAG system that wants maximum flexibility without breaking the bank!

---

**Status**: ✅ Production Ready
**Default**: Enabled in PageProcessor
**Cost Impact**: < $0.02 per 1000 pages
**Performance**: No noticeable difference
