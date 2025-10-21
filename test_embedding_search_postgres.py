#!/usr/bin/env python3
"""
Test Embedding Search with PostgreSQL
"""

import os
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'
os.environ['USE_POSTGRESQL'] = 'true'

from dotenv import load_dotenv
from embedding_search import EmbeddingSearcher
from document_database_docker import DocumentDatabaseDocker

load_dotenv()

print("=" * 80)
print("🔍 Testing Embedding Search with PostgreSQL")
print("=" * 80)

# Step 1: Load existing documents from PostgreSQL
print("\n1️⃣  Loading documents from PostgreSQL...")
db = DocumentDatabaseDocker()
existing_docs = db.list_documents(limit=10)

print(f"   Loaded {len(existing_docs)} documents")
if existing_docs:
    print(f"\n   Sample document fields:")
    for key in existing_docs[0].keys():
        print(f"      • {key}")

# Step 2: Check if embeddings are included
print("\n2️⃣  Checking for embeddings...")
has_embeddings = 'embedding' in existing_docs[0] if existing_docs else False
print(f"   Has 'embedding' field: {has_embeddings}")

if not has_embeddings:
    print("\n   ❌ PROBLEM: Embeddings NOT included in list_documents()")
    print("   The embedding_search.py expects embeddings in the document dict!")
    print("\n   Solution needed: Update list_documents() to include embeddings")
else:
    print("   ✅ Embeddings are included!")

# Step 3: Test new topic
print("\n3️⃣  Testing with a new topic...")
new_topic = {
    "title": "EOS Smart Contract Testing",
    "category": "tutorial",
    "summary": "Learn how to test EOS smart contracts effectively",
    "description": "Complete guide to testing smart contracts on EOS Network"
}

# Initialize searcher
searcher = EmbeddingSearcher()

# Try to find similar documents
print(f"\n4️⃣  Searching for similar documents...")
try:
    results = searcher.find_similar_documents(new_topic, existing_docs)

    print(f"\n   Found {len(results)} results:")
    for doc, similarity, action in results[:3]:
        if doc:
            print(f"      • {doc['title'][:50]}: {similarity:.3f} → {action}")
        else:
            print(f"      • No match: {similarity:.3f} → {action}")

except Exception as e:
    print(f"\n   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
