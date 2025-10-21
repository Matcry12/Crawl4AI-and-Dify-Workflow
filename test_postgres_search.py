#!/usr/bin/env python3
"""
Test PostgreSQL vector similarity search
"""

import os
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

import sys
import json
import subprocess
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

print("=" * 80)
print("🔍 Testing PostgreSQL Vector Search")
print("=" * 80)

# Test query
query = "How do I report bugs in Python?"
print(f"\n📝 Query: \"{query}\"")

# Generate embedding
print("\n1. Generating query embedding...")
result = genai.embed_content(
    model="models/text-embedding-004",
    content=query,
    task_type="retrieval_query"
)
query_embedding = result['embedding']
print(f"   ✓ Generated 768-dimensional embedding")

# Format as PostgreSQL array
emb_str = ','.join(str(x) for x in query_embedding)
emb_array = f"ARRAY[{emb_str}]::vector"

# Search for similar documents
print("\n2. Searching for similar documents...")
sql = f"""
SELECT
    id,
    title,
    category,
    mode,
    (1 - (embedding <=> {emb_array})) AS similarity
FROM documents
WHERE embedding IS NOT NULL
ORDER BY embedding <=> {emb_array}
LIMIT 5;
"""

result = subprocess.run(
    ['docker', 'exec', 'docker-db-1',
     'psql', '-U', 'postgres', '-d', 'crawl4ai',
     '-c', sql],
    capture_output=True,
    text=True
)

print(result.stdout)

# Test with different query
print("\n" + "=" * 80)
query2 = "EOS smart contract development"
print(f"📝 Query: \"{query2}\"")

result2 = genai.embed_content(
    model="models/text-embedding-004",
    content=query2,
    task_type="retrieval_query"
)
query_embedding2 = result2['embedding']

emb_str2 = ','.join(str(x) for x in query_embedding2)
emb_array2 = f"ARRAY[{emb_str2}]::vector"

sql2 = f"""
SELECT
    id,
    title,
    category,
    (1 - (embedding <=> {emb_array2})) AS similarity
FROM documents
WHERE embedding IS NOT NULL
ORDER BY embedding <=> {emb_array2}
LIMIT 5;
"""

result = subprocess.run(
    ['docker', 'exec', 'docker-db-1',
     'psql', '-U', 'postgres', '-d', 'crawl4ai',
     '-c', sql2],
    capture_output=True,
    text=True
)

print(result.stdout)

print("=" * 80)
print("✅ Vector search test complete!")
print("=" * 80)
