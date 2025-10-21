#!/usr/bin/env python3
"""
Simple migration: Read SQLite locally, insert via docker exec psql
"""

import os
import json
import sqlite3
import subprocess
import sys

print("=" * 80)
print("🚀 SQLite → PostgreSQL Migration")
print("=" * 80)

# Connect to SQLite
if not os.path.exists('documents.db'):
    print("\n❌ documents.db not found")
    sys.exit(1)

conn = sqlite3.connect('documents.db')
conn.row_factory = sqlite3.Row

cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM documents")
total = cursor.fetchone()[0]

print(f"\n📋 Found {total} documents in SQLite")

# Get all documents
cursor.execute("""
    SELECT id, title, content, category, mode, embedding, metadata
    FROM documents
""")

documents = cursor.fetchall()

print(f"\n🔄 Migrating to PostgreSQL...")

migrated = 0
errors = 0

for i, doc in enumerate(documents, 1):
    try:
        # Prepare values
        doc_id = doc['id']
        title = doc['title'].replace("'", "''")
        content = doc['content'].replace("'", "''")
        category = doc['category'] or ''
        mode = doc['mode'] or ''

        # Parse embedding
        embedding_array = "NULL"
        if doc['embedding'] and doc['embedding'] != 'null':
            try:
                emb_list = json.loads(doc['embedding'])
                # Format as PostgreSQL array
                emb_str = ','.join(str(x) for x in emb_list)
                embedding_array = f"ARRAY[{emb_str}]::vector"
            except:
                pass

        # Build SQL
        sql = f"""
INSERT INTO documents (id, title, content, category, mode, embedding, metadata)
VALUES (
    '{doc_id}',
    '{title}',
    '{content}',
    {f"'{category}'" if category else 'NULL'},
    {f"'{mode}'" if mode else 'NULL'},
    {embedding_array},
    '{{}}'::jsonb
)
ON CONFLICT (id) DO UPDATE
SET title = EXCLUDED.title,
    content = EXCLUDED.content,
    embedding = EXCLUDED.embedding;
"""

        # Execute via docker exec
        result = subprocess.run(
            ['docker', 'exec', 'docker-db-1',
             'psql', '-U', 'postgres', '-d', 'crawl4ai', '-c', sql],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            migrated += 1
            if i % 10 == 0 or i == total:
                print(f"   [{i}/{total}] Migrated {migrated} documents...")
        else:
            errors += 1
            if errors <= 3:  # Only show first 3 errors
                print(f"   ✗ Error #{errors}: {result.stderr[:100]}")

    except Exception as e:
        errors += 1
        if errors <= 3:
            print(f"   ✗ Error: {e}")

print(f"\n{'=' * 80}")
print(f"📊 MIGRATION COMPLETE")
print(f"{'=' * 80}")
print(f"Total documents: {total}")
print(f"✅ Migrated: {migrated}")
print(f"❌ Errors: {errors}")

# Verify
result = subprocess.run(
    ['docker', 'exec', 'docker-db-1',
     'psql', '-U', 'postgres', '-d', 'crawl4ai', '-t', '-A',
     '-c', 'SELECT COUNT(*) FROM documents;'],
    capture_output=True,
    text=True
)

pg_count = int(result.stdout.strip()) if result.stdout.strip() else 0

result = subprocess.run(
    ['docker', 'exec', 'docker-db-1',
     'psql', '-U', 'postgres', '-d', 'crawl4ai', '-t', '-A',
     '-c', 'SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL;'],
    capture_output=True,
    text=True
)

pg_with_emb = int(result.stdout.strip()) if result.stdout.strip() else 0

print(f"\n📊 PostgreSQL Verification:")
print(f"   Total documents: {pg_count}")
print(f"   With embeddings: {pg_with_emb}")

if pg_count == total:
    print(f"\n✅ VERIFICATION PASSED - All documents migrated!")
    sys.exit(0)
else:
    print(f"\n⚠️  Count mismatch (expected {total}, got {pg_count})")
    sys.exit(1)
