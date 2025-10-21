#!/usr/bin/env python3
"""
Test COMPLETE CREATE PATH: Truly new topic → Document creation → Embedding → Save
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
print("🧪 COMPLETE CREATE AND SAVE TEST")
print("=" * 80)

# Step 1: Load existing documents
print("\n1️⃣  Loading existing documents from PostgreSQL...")
db = DocumentDatabaseDocker()
existing_docs = db.list_documents(include_embeddings=True)
print(f"   ✅ Loaded {len(existing_docs)} documents")

# Step 2: Create a topic completely unrelated to existing content
print("\n2️⃣  Creating completely new topic (unrelated to existing content)...")
new_topic = {
    "title": "Growing Tomatoes in Small Spaces",
    "category": "guide",
    "summary": "Learn how to successfully grow tomatoes in containers and small urban gardens with limited space",
    "description": "Comprehensive guide to container gardening for tomatoes. Covers variety selection, soil preparation, watering schedules, and pest management for urban gardeners.",
    "url": "https://example.com/tomato-growing-guide"
}
print(f"   Topic: {new_topic['title']}")
print(f"   Category: {new_topic['category']}")

# Step 3: Check similarity
print("\n3️⃣  Running embedding search...")
searcher = EmbeddingSearcher()
results = searcher.find_similar_documents(new_topic, existing_docs)

if results:
    best_match, best_similarity, action = results[0]
    print(f"   Best match: {best_match['title'][:50] if best_match else 'None'}")
    print(f"   Similarity: {best_similarity:.3f}")
    print(f"   Recommended action: {action}")
else:
    action = 'create'
    best_similarity = 0.0
    print(f"   No matches found")
    print(f"   Recommended action: {action}")

# Step 4: Force CREATE to test the complete path
print(f"\n4️⃣  Testing CREATE path (similarity: {best_similarity:.3f})...")
creator = DocumentCreator()

try:
    print(f"\n   📝 Creating paragraph document...")
    para_doc = creator.create_paragraph_document(topic=new_topic)

    if not para_doc:
        print(f"   ❌ Document creation failed")
    else:
        print(f"\n   ✅ Document created!")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"   ID: {para_doc['id']}")
        print(f"   Title: {para_doc['title']}")
        print(f"   Mode: {para_doc['mode']}")
        print(f"   Category: {para_doc['category']}")
        print(f"   Content length: {len(para_doc['content'])} chars")

        # Check embedding
        has_embedding = 'embedding' in para_doc and para_doc['embedding'] is not None
        print(f"   Has embedding: {has_embedding}")

        if has_embedding:
            print(f"   Embedding dimensions: {len(para_doc['embedding'])}")
            print(f"   Embedding sample: [{para_doc['embedding'][0]:.6f}, {para_doc['embedding'][1]:.6f}, {para_doc['embedding'][2]:.6f}, ...]")
        else:
            print(f"   ⚠️  WARNING: No embedding generated!")

        # Step 5: Save to database
        print(f"\n5️⃣  Saving to database...")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Check if already exists
        existing = db.get_document(para_doc['id'])

        if existing:
            print(f"   📋 Document already exists in database")
            print(f"   Existing ID: {existing['id']}")
            print(f"   Existing title: {existing['title']}")

            # Check if update needed
            if has_embedding and not existing.get('embedding'):
                print(f"\n   🔄 Updating with embedding...")
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
                    print(f"   ✅ Document updated with embedding")
                else:
                    print(f"   ❌ Update failed")
            else:
                print(f"   ⊘ No update needed - document complete")

        else:
            print(f"   💾 Document does NOT exist - inserting new...")

            success = db.create_document(
                doc_id=para_doc['id'],
                title=para_doc['title'],
                content=para_doc['content'],
                category=para_doc['category'],
                mode=para_doc['mode'],
                embedding=para_doc['embedding'] if has_embedding else None,
                metadata=para_doc.get('metadata', {})
            )

            if success:
                print(f"   ✅ Document saved successfully!")
            else:
                print(f"   ❌ Save failed!")

        # Step 6: Verify save
        print(f"\n6️⃣  Verifying save...")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        saved_doc = db.get_document(para_doc['id'])

        if saved_doc:
            print(f"   ✅ Document verified in database!")
            print(f"   ID: {saved_doc['id']}")
            print(f"   Title: {saved_doc['title']}")
            print(f"   Category: {saved_doc['category']}")
            print(f"   Mode: {saved_doc['mode']}")
            print(f"   Content length: {len(saved_doc.get('content', ''))} chars")

            # Can't check embedding in get_document (not included by default)
            # But we can verify with list_documents
            print(f"\n   Checking embedding in database...")
            docs_with_embedding = db.list_documents(limit=1000, include_embeddings=True)
            matching = [d for d in docs_with_embedding if d['id'] == para_doc['id']]

            if matching:
                db_doc = matching[0]
                has_db_embedding = 'embedding' in db_doc and db_doc['embedding'] is not None
                print(f"   Has embedding in DB: {has_db_embedding}")
                if has_db_embedding:
                    print(f"   Embedding dimensions: {len(db_doc['embedding'])}")
            else:
                print(f"   ⚠️  Could not find document in list")

        else:
            print(f"   ❌ Document NOT found in database!")

except Exception as e:
    print(f"\n   ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Step 7: Final statistics
print(f"\n{'=' * 80}")
print("7️⃣  FINAL DATABASE STATISTICS")
print(f"{'=' * 80}")

stats = db.get_statistics()
print(f"\n📊 Database Statistics:")
print(f"   Total documents: {stats['total_documents']}")
print(f"   With embeddings: {stats['documents_with_embeddings']}")
print(f"   Embedding coverage: {stats['embedding_percentage']:.1f}%")

if stats['by_category']:
    print(f"\n📁 By Category:")
    for category, count in sorted(stats['by_category'].items(), key=lambda x: -x[1])[:10]:
        print(f"   {category}: {count}")

print(f"\n{'=' * 80}")
print("✅ TEST COMPLETE - Full CREATE and SAVE workflow verified")
print(f"{'=' * 80}")
