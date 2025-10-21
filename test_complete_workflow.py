#!/usr/bin/env python3
"""
Complete Workflow Test: Topic Extraction → Embedding Search → Document Creation → Database Save
Tests the entire pipeline including merge and create nodes
"""

import os
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'
os.environ['USE_POSTGRESQL'] = 'true'

import json
from dotenv import load_dotenv
from document_database_docker import DocumentDatabaseDocker
from embedding_search import EmbeddingSearcher
from document_creator import DocumentCreator

load_dotenv()

print("=" * 80)
print("🧪 COMPLETE WORKFLOW TEST")
print("=" * 80)

# Step 1: Load existing documents from PostgreSQL
print("\n1️⃣  Loading existing documents from PostgreSQL...")
db = DocumentDatabaseDocker()
existing_docs = db.list_documents(include_embeddings=True)
print(f"   ✅ Loaded {len(existing_docs)} documents")

# Verify embeddings are included
if existing_docs:
    has_embeddings = 'embedding' in existing_docs[0]
    print(f"   Embeddings included: {has_embeddings}")
    if has_embeddings and existing_docs[0]['embedding']:
        print(f"   Embedding dimensions: {len(existing_docs[0]['embedding'])}")

# Step 2: Load test topics from the crawl
print("\n2️⃣  Loading test topics from crawl...")
topics_file = "/home/matcry/Documents/Crawl4AI/bfs_crawled/topics_report.json"
with open(topics_file, 'r') as f:
    topics_data = json.load(f)

# Extract all topics
all_topics = []
for url, topics in topics_data.items():
    for topic in topics:
        topic['url'] = url
        all_topics.append(topic)

print(f"   ✅ Loaded {len(all_topics)} topics from crawl")
print(f"   Topics: {[t['title'][:40] + '...' for t in all_topics]}")

# Step 3: Run embedding search to determine actions
print("\n3️⃣  Running embedding search for each topic...")
searcher = EmbeddingSearcher()

actions_summary = {
    'create': [],
    'merge': [],
    'verify': []
}

topic_results = []

for i, topic in enumerate(all_topics, 1):
    print(f"\n   [{i}/{len(all_topics)}] Processing: {topic['title'][:50]}...")

    try:
        # Find similar documents
        results = searcher.find_similar_documents(topic, existing_docs)

        if results:
            best_match, best_similarity, action = results[0]
            print(f"        Best match: {best_match['title'][:40] if best_match else 'None'}")
            print(f"        Similarity: {best_similarity:.3f}")
            print(f"        Action: {action}")

            actions_summary[action].append(topic['title'])
            topic_results.append({
                'topic': topic,
                'action': action,
                'best_match': best_match,
                'similarity': best_similarity
            })
        else:
            print(f"        No results - Action: create")
            actions_summary['create'].append(topic['title'])
            topic_results.append({
                'topic': topic,
                'action': 'create',
                'best_match': None,
                'similarity': 0.0
            })

    except Exception as e:
        print(f"        ❌ Error: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("📊 EMBEDDING SEARCH SUMMARY")
print("=" * 80)
print(f"CREATE: {len(actions_summary['create'])} topics")
for title in actions_summary['create']:
    print(f"  • {title[:60]}")
print(f"\nMERGE: {len(actions_summary['merge'])} topics")
for title in actions_summary['merge']:
    print(f"  • {title[:60]}")
print(f"\nVERIFY: {len(actions_summary['verify'])} topics")
for title in actions_summary['verify']:
    print(f"  • {title[:60]}")

# Step 4: Create documents for topics that need creation
print("\n" + "=" * 80)
print("4️⃣  CREATING DOCUMENTS")
print("=" * 80)

creator = DocumentCreator()

# Test with one CREATE topic
create_topics = [r for r in topic_results if r['action'] == 'create']
if create_topics:
    print(f"\n📝 Testing document creation with {len(create_topics)} CREATE topics...")
    test_topic = create_topics[0]['topic']

    print(f"\nCreating document for: {test_topic['title']}")
    print(f"Category: {test_topic['category']}")

    try:
        # Create paragraph document
        print("\n   Creating paragraph document...")
        para_doc = creator.create_paragraph_document(
            topic=test_topic,
            url=test_topic['url']
        )

        if para_doc:
            print(f"   ✅ Document created: {para_doc['id']}")
            print(f"   Title: {para_doc['title']}")
            print(f"   Mode: {para_doc['mode']}")
            print(f"   Has embedding: {'embedding' in para_doc and para_doc['embedding'] is not None}")
            if 'embedding' in para_doc and para_doc['embedding']:
                print(f"   Embedding dimensions: {len(para_doc['embedding'])}")
        else:
            print("   ❌ Document creation failed")

    except Exception as e:
        print(f"   ❌ Error creating document: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\n⚠️  No CREATE topics found - all topics match existing documents")

# Step 5: Save documents to database
print("\n" + "=" * 80)
print("5️⃣  SAVING DOCUMENTS TO DATABASE")
print("=" * 80)

if create_topics and para_doc:
    print(f"\nAttempting to save document: {para_doc['id']}")

    try:
        # Check if document already exists
        existing = db.get_document(para_doc['id'])

        if existing:
            print(f"   📋 Document already exists: {para_doc['id']}")
            print(f"   Checking if update needed...")

            if para_doc.get('embedding') and not existing.get('embedding'):
                print(f"   🔄 Updating with embedding...")
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
                    print(f"   ✅ Document updated successfully")
                else:
                    print(f"   ❌ Update failed")
            else:
                print(f"   ⊘ Skipping - document complete")
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
                print(f"   ✅ Document saved successfully")
            else:
                print(f"   ❌ Save failed")

    except Exception as e:
        print(f"   ❌ Error saving document: {e}")
        import traceback
        traceback.print_exc()

# Step 6: Verify final state
print("\n" + "=" * 80)
print("6️⃣  VERIFICATION")
print("=" * 80)

stats = db.get_statistics()
print(f"\n📊 Database Statistics:")
print(f"   Total documents: {stats['total_documents']}")
print(f"   With embeddings: {stats['documents_with_embeddings']}")
print(f"   Embedding coverage: {stats['embedding_percentage']:.1f}%")

if stats['by_category']:
    print(f"\n📁 By Category:")
    for category, count in stats['by_category'].items():
        print(f"   {category}: {count}")

if stats['by_mode']:
    print(f"\n🔧 By Mode:")
    for mode, count in stats['by_mode'].items():
        print(f"   {mode}: {count}")

print("\n" + "=" * 80)
print("✅ COMPLETE WORKFLOW TEST FINISHED")
print("=" * 80)
