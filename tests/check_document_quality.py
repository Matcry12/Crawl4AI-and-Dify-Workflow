#!/usr/bin/env python3
"""Check the quality of documents in the database"""

import os
from chunked_document_database import ChunkedDocumentDatabase

# Get API key from environment
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

print("=" * 80)
print("📊 DOCUMENT QUALITY ASSESSMENT")
print("=" * 80)
print()

# Initialize database
db = ChunkedDocumentDatabase()

# Get all documents
documents = db.get_all_documents_with_embeddings()

print(f"Total documents: {len(documents)}")
print()

# Analyze each document
for i, doc in enumerate(documents, 1):
    doc_id = doc['id']

    # Get full document with content
    full_doc = db.get_document_by_id(doc_id)

    if not full_doc:
        print(f"{i}. ❌ Could not retrieve: {doc['title']}")
        continue

    # Calculate metrics
    title = full_doc['title']
    content_len = len(full_doc['content'])
    summary_len = len(full_doc['summary'])
    num_chunks = len(full_doc['chunks'])
    num_keywords = len(full_doc['keywords'])
    category = full_doc['category']

    # Quality checks
    issues = []

    # Check content length
    if content_len < 500:
        issues.append("⚠️  Very short content")
    elif content_len < 1000:
        issues.append("⚠️  Short content")

    # Check summary
    if summary_len < 100:
        issues.append("⚠️  Very short summary")

    # Check keywords
    if num_keywords < 3:
        issues.append("⚠️  Too few keywords")

    # Check chunks
    if num_chunks == 0:
        issues.append("❌ No chunks")
    elif num_chunks == 1:
        issues.append("⚠️  Only 1 chunk")

    # Check for content quality indicators
    content_lower = full_doc['content'].lower()

    # Check for meaningful content
    has_technical_terms = any(term in content_lower for term in [
        'contract', 'blockchain', 'eos', 'function', 'transaction',
        'account', 'resource', 'network', 'staking', 'token'
    ])

    if not has_technical_terms:
        issues.append("⚠️  May lack technical content")

    # Check for structure indicators
    has_structure = any(indicator in full_doc['content'] for indicator in [
        '\n\n', '  ', '\t'  # paragraphs, indentation
    ])

    # Display results
    quality_icon = "✅" if len(issues) == 0 else "⚠️" if len(issues) <= 2 else "❌"

    print(f"{quality_icon} {i}. {title}")
    print(f"   Category: {category}")
    print(f"   Content: {content_len} chars | Summary: {summary_len} chars")
    print(f"   Chunks: {num_chunks} | Keywords: {num_keywords}")
    print(f"   Keywords: {', '.join(full_doc['keywords'][:5])}")

    if issues:
        print(f"   Issues:")
        for issue in issues:
            print(f"      {issue}")

    # Show content preview
    preview = full_doc['content'][:200].replace('\n', ' ')
    print(f"   Preview: {preview}...")

    print()

# Overall statistics
print("=" * 80)
print("📈 OVERALL STATISTICS")
print("=" * 80)
print()

total_content = sum(len(db.get_document_by_id(doc['id'])['content']) for doc in documents)
avg_content = total_content / len(documents) if documents else 0

total_chunks = sum(len(db.get_document_by_id(doc['id'])['chunks']) for doc in documents)
avg_chunks = total_chunks / len(documents) if documents else 0

categories = {}
for doc in documents:
    full_doc = db.get_document_by_id(doc['id'])
    cat = full_doc['category']
    categories[cat] = categories.get(cat, 0) + 1

print(f"Average content length: {avg_content:.0f} chars")
print(f"Total chunks: {total_chunks}")
print(f"Average chunks per document: {avg_chunks:.1f}")
print()
print("Categories:")
for cat, count in sorted(categories.items()):
    print(f"  - {cat}: {count} documents")
print()

# Quality score
high_quality = sum(1 for doc in documents
                   if len(db.get_document_by_id(doc['id'])['content']) >= 1000
                   and len(db.get_document_by_id(doc['id'])['chunks']) >= 2)
quality_pct = (high_quality / len(documents) * 100) if documents else 0

print(f"High quality documents (>1000 chars, ≥2 chunks): {high_quality}/{len(documents)} ({quality_pct:.0f}%)")
print()
