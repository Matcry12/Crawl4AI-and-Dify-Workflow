#!/usr/bin/env python3
"""
Test the CREATE path: New topic → Document creation → Embedding generation → Save to database
"""

import os
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'
os.environ['USE_POSTGRESQL'] = 'true'

from dotenv import load_dotenv
from document_database_docker import DocumentDatabaseDocker
from embedding_search import EmbeddingSearcher
from document_creator import DocumentCreator

load_dotenv()

print("=" * 80)
print("🧪 TEST CREATE PATH")
print("=" * 80)

# Step 1: Load existing documents
print("\n1️⃣  Loading existing documents from PostgreSQL...")
db = DocumentDatabaseDocker()
existing_docs = db.list_documents(include_embeddings=True)
print(f"   ✅ Loaded {len(existing_docs)} documents")

# Step 2: Create a completely NEW topic (not in database)
print("\n2️⃣  Creating a new test topic...")
new_topic = {
    "title": "Rust Smart Contract Development on Solana",
    "category": "tutorial",
    "summary": "Learn how to build high-performance smart contracts on Solana blockchain using Rust programming language",
    "description": "Complete guide to Solana smart contract development with Rust. Covers Anchor framework, program architecture, and deployment.",
    "url": "https://example.com/solana-rust-tutorial"
}
print(f"   Topic: {new_topic['title']}")
print(f"   Category: {new_topic['category']}")

# Step 3: Check if it matches any existing documents
print("\n3️⃣  Running embedding search...")
searcher = EmbeddingSearcher()
results = searcher.find_similar_documents(new_topic, existing_docs)

if results:
    best_match, best_similarity, action = results[0]
    print(f"   Best match: {best_match['title'][:50] if best_match else 'None'}")
    print(f"   Similarity: {best_similarity:.3f}")
    print(f"   Action: {action}")
else:
    action = 'create'
    print(f"   No matches found - Action: {action}")

# Step 4: Create document if action is CREATE
if action == 'create':
    print("\n4️⃣  Creating document...")
    creator = DocumentCreator()

    try:
        # Create paragraph document
        para_doc = creator.create_paragraph_document(
            topic=new_topic,
            url=new_topic['url']
        )

        if para_doc:
            print(f"\n   ✅ Document created successfully!")
            print(f"   ID: {para_doc['id']}")
            print(f"   Title: {para_doc['title']}")
            print(f"   Mode: {para_doc['mode']}")
            print(f"   Category: {para_doc['category']}")
            print(f"   Content length: {len(para_doc['content'])} chars")
            print(f"   Has embedding: {'embedding' in para_doc and para_doc['embedding'] is not None}")

            if 'embedding' in para_doc and para_doc['embedding']:
                print(f"   Embedding dimensions: {len(para_doc['embedding'])}")
                print(f"   Embedding sample: [{para_doc['embedding'][0]:.4f}, {para_doc['embedding'][1]:.4f}, ...]")

            # Step 5: Save to database
            print("\n5️⃣  Saving to database...")

            # Check if it already exists
            existing = db.get_document(para_doc['id'])

            if existing:
                print(f"   📋 Document already exists: {para_doc['id']}")
                print(f"   Skipping save")
            else:
                print(f"   💾 Inserting new document...")
                success = db.create_document(
                    doc_id=para_doc['id'],
                    title=para_doc['title'],
                    content=para_doc['content'],
                    category=para_doc['category'],
                    mode=para_doc['mode'],
                    embedding=para_doc['embedding'],
                    metadata=para_doc.get('metadata', {})
                )

                if success:
                    print(f"   ✅ Document saved successfully!")

                    # Verify it was saved
                    print("\n6️⃣  Verifying save...")
                    saved_doc = db.get_document(para_doc['id'])
                    if saved_doc:
                        print(f"   ✅ Document verified in database")
                        print(f"   ID: {saved_doc['id']}")
                        print(f"   Title: {saved_doc['title']}")
                        print(f"   Category: {saved_doc['category']}")
                        print(f"   Mode: {saved_doc['mode']}")
                    else:
                        print(f"   ❌ Document NOT found in database!")
                else:
                    print(f"   ❌ Save failed")

        else:
            print("   ❌ Document creation failed")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

elif action == 'merge':
    print("\n4️⃣  MERGE action detected")
    print(f"   This topic is very similar to: {best_match['title']}")
    print(f"   Similarity: {best_similarity:.3f}")
    print(f"   In production, this would trigger document merger")

elif action == 'verify':
    print("\n4️⃣  VERIFY action detected")
    print(f"   Potential match: {best_match['title'][:50]}")
    print(f"   Similarity: {best_similarity:.3f}")
    print(f"   In production, this would require LLM verification")

# Final statistics
print("\n" + "=" * 80)
print("7️⃣  FINAL DATABASE STATISTICS")
print("=" * 80)

stats = db.get_statistics()
print(f"\n📊 Database Statistics:")
print(f"   Total documents: {stats['total_documents']}")
print(f"   With embeddings: {stats['documents_with_embeddings']}")
print(f"   Embedding coverage: {stats['embedding_percentage']:.1f}%")

if stats['by_category']:
    print(f"\n📁 By Category:")
    for category, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
        print(f"   {category}: {count}")

if stats['by_mode']:
    print(f"\n🔧 By Mode:")
    for mode, count in stats['by_mode'].items():
        print(f"   {mode}: {count}")

print("\n" + "=" * 80)
print("✅ TEST COMPLETE")
print("=" * 80)
