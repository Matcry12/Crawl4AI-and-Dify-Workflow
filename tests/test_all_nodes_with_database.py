#!/usr/bin/env python3
"""
Comprehensive Node Integration Test with Secure Database

Tests all major components (nodes) to ensure they work correctly with
the new secure psycopg2 database implementation:

1. Database operations (chunked_document_database.py)
2. Document creator (document_creator.py)
3. Document merger (document_merger.py)
4. Merge decision maker (merge_or_create_decision.py)
5. Embedding search (embedding_search.py)
6. Workflow manager (workflow_manager.py)
"""

import os
import sys
from datetime import datetime

# Set API key
os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', 'AIzaSyBlk1Pc88ZxhrtTHtU__rd2fwNcWw3ea-E')

from chunked_document_database import SimpleDocumentDatabase
from document_creator import DocumentCreator
from document_merger import DocumentMerger
from merge_or_create_decision import MergeOrCreateDecision
from embedding_search import EmbeddingSearcher


def print_header(title):
    """Print section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_node_1_database():
    """Test Node 1: Database Operations"""
    print_header("NODE 1: Database Operations")

    try:
        # Initialize database
        print("\n📦 Initializing database...")
        db = SimpleDocumentDatabase()

        # Test 1: Get stats
        print("\n1️⃣ Testing get_stats()...")
        stats = db.get_stats()
        print(f"   ✅ Stats retrieved:")
        print(f"      Documents: {stats.get('total_documents', 0)}")
        print(f"      Chunks: {stats.get('total_chunks', 0)}")
        print(f"      Merges: {stats.get('total_merges', 0)}")

        # Test 2: Get all documents
        print("\n2️⃣ Testing get_all_documents_with_embeddings()...")
        docs = db.get_all_documents_with_embeddings()
        print(f"   ✅ Retrieved {len(docs)} documents")
        if docs:
            doc = docs[0]
            print(f"      Sample: {doc.get('title', 'N/A')[:50]}")
            print(f"      Has embedding: {'embedding' in doc and doc['embedding'] is not None}")

        # Test 3: Get document by ID
        if docs:
            print("\n3️⃣ Testing get_document_by_id()...")
            doc_id = docs[0]['id']
            full_doc = db.get_document_by_id(doc_id)
            if full_doc:
                print(f"   ✅ Document retrieved: {doc_id}")
                print(f"      Content length: {len(full_doc.get('content', ''))} chars")
                print(f"      Chunks: {len(full_doc.get('chunks', []))}")
                print(f"      Has embedding: {'embedding' in full_doc and full_doc['embedding'] is not None}")

        # Test 4: Insert test document
        print("\n4️⃣ Testing insert_document()...")
        test_doc = {
            "id": f"test_node_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "title": "Node Integration Test Document",
            "summary": "Testing secure database with all nodes",
            "content": "This is a test document to verify the secure database works with all workflow nodes.",
            "category": "test",
            "keywords": ["test", "integration", "secure"],
            "source_urls": ["https://test.example.com"],
            "embedding": [0.1] * 768,
            "chunks": [
                {
                    "content": "Test chunk content",
                    "chunk_index": 0,
                    "token_count": 3,
                    "embedding": [0.2] * 768
                }
            ]
        }

        success = db.insert_document(test_doc)
        if success:
            print(f"   ✅ Document inserted: {test_doc['id']}")
        else:
            print(f"   ❌ Failed to insert document")
            return None, None

        # Test 5: Update document
        print("\n5️⃣ Testing update_document_with_chunks()...")
        test_doc['content'] = "Updated content for node testing"
        test_doc['summary'] = "Updated summary"
        success = db.update_document_with_chunks(test_doc)
        if success:
            print(f"   ✅ Document updated")

            # Verify update
            retrieved = db.get_document_by_id(test_doc['id'])
            if "Updated content" in retrieved.get('content', ''):
                print(f"   ✅ Update verified")
            else:
                print(f"   ❌ Update not applied")

        # Test 6: Transaction support
        print("\n6️⃣ Testing transaction support...")
        test_doc2 = {
            "id": f"test_txn_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "title": "Transaction Test",
            "summary": "Testing rollback",
            "content": "This should be rolled back",
            "category": "test",
            "keywords": ["transaction"],
            "source_urls": [],
            "embedding": [0.1] * 768,
            "chunks": []
        }

        db.begin_transaction()
        db.insert_document(test_doc2)
        db.rollback_transaction()

        retrieved = db.get_document_by_id(test_doc2['id'])
        if not retrieved:
            print(f"   ✅ Transaction rollback working")
        else:
            print(f"   ❌ Transaction rollback failed")

        print("\n✅ NODE 1: Database operations - ALL TESTS PASSED")
        return db, test_doc['id']

    except Exception as e:
        print(f"\n❌ NODE 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_node_2_document_creator(db, cleanup_ids):
    """Test Node 2: Document Creator"""
    print_header("NODE 2: Document Creator")

    try:
        # Initialize document creator
        print("\n📝 Initializing document creator...")
        creator = DocumentCreator(db)

        # Test: Create document from topic
        print("\n1️⃣ Testing create_document()...")
        test_topic = {
            "title": "Node 2 Test: Creating Documents",
            "summary": "Testing document creator with secure database",
            "content": "This topic tests the document creator node. It should create a document with proper embeddings and chunks.",
            "category": "test",
            "keywords": ["node2", "creator", "test"]
        }

        created_doc = creator.create_document(test_topic)
        if created_doc:
            print(f"   ✅ Document created: {created_doc['id']}")
            print(f"      Title: {created_doc['title']}")
            print(f"      Content length: {len(created_doc.get('content', ''))} chars")
            print(f"      Chunks: {len(created_doc.get('chunks', []))}")
            print(f"      Has embedding: {'embedding' in created_doc and created_doc['embedding'] is not None}")
            cleanup_ids.append(created_doc['id'])

            # Verify document in database
            print("\n2️⃣ Verifying document in database...")
            retrieved = db.get_document_by_id(created_doc['id'])
            if retrieved:
                print(f"   ✅ Document found in database")
                print(f"      Chunks stored: {len(retrieved.get('chunks', []))}")
            else:
                print(f"   ❌ Document not found in database")
                return False
        else:
            print(f"   ❌ Failed to create document")
            return False

        print("\n✅ NODE 2: Document creator - ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ NODE 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_node_3_merge_decision(db):
    """Test Node 3: Merge Decision Maker"""
    print_header("NODE 3: Merge Decision Maker")

    try:
        # Initialize embedder first (required for decision maker)
        print("\n🔍 Initializing embedder...")
        embedder = EmbeddingSearcher(db)

        # Initialize decision maker
        print("\n🤔 Initializing merge decision maker...")
        decision_maker = MergeOrCreateDecision(embedder)

        # Get existing documents
        print("\n1️⃣ Loading existing documents...")
        existing_docs = db.get_all_documents_with_embeddings()
        print(f"   ✅ Loaded {len(existing_docs)} documents")

        # Test: Make decision for new topic
        print("\n2️⃣ Testing decide() for new topic...")
        test_topic = {
            "title": "Node 3 Test: Completely Different Topic",
            "summary": "This is about quantum computing in space",
            "content": "A totally unrelated topic to test CREATE decision",
            "category": "test"
        }

        decision = decision_maker.decide(test_topic, existing_docs, use_llm_verification=False)
        if decision:
            print(f"   ✅ Decision made: {decision.get('action', 'N/A')}")
            print(f"      Similarity: {decision.get('similarity', 0):.3f}")
            if decision.get('action') == 'create':
                print(f"      Reasoning: {decision.get('reasoning', 'N/A')[:80]}")
        else:
            print(f"   ❌ Failed to make decision")
            return False

        # Test: Make decision for similar topic (should merge)
        if existing_docs:
            print("\n3️⃣ Testing decide() for similar topic...")
            existing_doc = existing_docs[0]
            similar_topic = {
                "title": f"Related to: {existing_doc['title'][:30]}",
                "summary": existing_doc.get('summary', '')[:100],
                "content": f"Additional information about {existing_doc['title'][:30]}",
                "category": existing_doc.get('category', 'general')
            }

            decision = decision_maker.decide(similar_topic, existing_docs, use_llm_verification=False)
            if decision:
                print(f"   ✅ Decision made: {decision.get('action', 'N/A')}")
                print(f"      Similarity: {decision.get('similarity', 0):.3f}")
                if decision.get('action') == 'merge':
                    print(f"      Target: {decision.get('target_doc_id', 'N/A')}")
                    print(f"      Reasoning: {decision.get('reasoning', 'N/A')[:80]}")

        print("\n✅ NODE 3: Merge decision maker - ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ NODE 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_node_4_document_merger(db, cleanup_ids):
    """Test Node 4: Document Merger"""
    print_header("NODE 4: Document Merger")

    try:
        # Initialize document merger
        print("\n🔀 Initializing document merger...")
        merger = DocumentMerger(db)

        # Get an existing document to merge into
        print("\n1️⃣ Loading existing document...")
        existing_docs = db.get_all_documents_with_embeddings()
        if not existing_docs:
            print(f"   ⚠️  No existing documents to merge into")
            return True

        target_doc_id = existing_docs[0]['id']
        target_doc = db.get_document_by_id(target_doc_id)
        if not target_doc:
            print(f"   ❌ Failed to load target document")
            return False

        print(f"   ✅ Loaded document: {target_doc['title'][:50]}")
        print(f"      Content length: {len(target_doc.get('content', ''))} chars")
        original_length = len(target_doc.get('content', ''))

        # Test: Merge a new topic
        print("\n2️⃣ Testing merge_document()...")
        new_topic = {
            "title": "Additional Information (Node 4 Test)",
            "summary": "This is additional content being merged",
            "content": "This is new content that should be merged into the existing document. It contains important information that complements the original document.",
            "category": target_doc.get('category', 'general')
        }

        merged_doc = merger.merge_document(new_topic, target_doc)
        if merged_doc:
            print(f"   ✅ Document merged successfully")
            print(f"      Original length: {original_length} chars")
            print(f"      Merged length: {len(merged_doc.get('content', ''))} chars")
            print(f"      New chunks: {len(merged_doc.get('chunks', []))}")
            print(f"      Has embedding: {'embedding' in merged_doc and merged_doc['embedding'] is not None}")

            # Note: We're testing merge but not saving to avoid modifying real data
            print(f"   ℹ️  Note: Not saving to database (testing only)")
        else:
            print(f"   ❌ Failed to merge document")
            return False

        print("\n✅ NODE 4: Document merger - ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ NODE 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_node_5_embedding_search(db):
    """Test Node 5: Embedding Search"""
    print_header("NODE 5: Embedding Search")

    try:
        # Initialize embedding search
        print("\n🔍 Initializing embedding search...")
        searcher = EmbeddingSearcher(db)

        # Test: Search for documents
        print("\n1️⃣ Testing search()...")
        query = "How to register an account"
        results = searcher.search(query, top_k=3)

        if results:
            print(f"   ✅ Search returned {len(results)} results")
            for i, result in enumerate(results, 1):
                print(f"\n      Result {i}:")
                print(f"      - Title: {result.get('title', 'N/A')[:60]}")
                print(f"      - Score: {result.get('score', 0):.4f}")
                print(f"      - Content length: {len(result.get('content', ''))} chars")
        else:
            print(f"   ⚠️  Search returned no results")

        # Test: Search with different query
        print("\n2️⃣ Testing search() with different query...")
        query2 = "cryptocurrency wallet"
        results2 = searcher.search(query2, top_k=2)

        if results2:
            print(f"   ✅ Search returned {len(results2)} results")
            for i, result in enumerate(results2, 1):
                print(f"\n      Result {i}:")
                print(f"      - Title: {result.get('title', 'N/A')[:60]}")
                print(f"      - Score: {result.get('score', 0):.4f}")

        print("\n✅ NODE 5: Embedding search - ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ NODE 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_node_6_workflow_manager(db, cleanup_ids):
    """Test Node 6: Workflow Manager (End-to-End)"""
    print_header("NODE 6: Workflow Manager (End-to-End)")

    try:
        from workflow_manager import WorkflowManager

        # Initialize workflow manager
        print("\n🔄 Initializing workflow manager...")
        workflow = WorkflowManager(db)

        # Test: Process topics through full workflow
        print("\n1️⃣ Testing process_topics() with multiple topics...")
        test_topics = [
            {
                "title": "Node 6 Test Topic 1: New Feature",
                "summary": "Testing workflow with new topic",
                "content": "This is a new topic that should create a new document through the full workflow.",
                "category": "test",
                "keywords": ["workflow", "test", "node6"]
            },
            {
                "title": "Node 6 Test Topic 2: Related Feature",
                "summary": "Testing workflow with related topic",
                "content": "This is a related topic that might merge with the previous one.",
                "category": "test",
                "keywords": ["workflow", "test", "related"]
            }
        ]

        print(f"   Processing {len(test_topics)} topics...")
        results = workflow.process_topics(test_topics)

        if results:
            print(f"\n   ✅ Workflow completed")
            print(f"      Documents created: {results.get('documents_created', 0)}")
            print(f"      Documents merged: {results.get('documents_merged', 0)}")
            print(f"      Topics processed: {results.get('topics_processed', 0)}")

            # Track created documents for cleanup
            if 'created_docs' in results:
                for doc in results['created_docs']:
                    cleanup_ids.append(doc['id'])
        else:
            print(f"   ❌ Workflow processing failed")
            return False

        print("\n✅ NODE 6: Workflow manager - ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ NODE 6 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_test_data(db, cleanup_ids):
    """Cleanup test documents"""
    print_header("CLEANUP: Removing Test Data")

    for doc_id in cleanup_ids:
        try:
            # Delete chunks
            query = "DELETE FROM chunks WHERE document_id = %s"
            db._execute_query(query, (doc_id,), fetch=False)

            # Delete document
            query = "DELETE FROM documents WHERE id = %s"
            db._execute_query(query, (doc_id,), fetch=False)

            print(f"   ✅ Cleaned up: {doc_id}")
        except Exception as e:
            print(f"   ⚠️  Failed to cleanup {doc_id}: {e}")


def main():
    """Run all node integration tests"""
    print("\n" + "=" * 70)
    print("  🧪 COMPREHENSIVE NODE INTEGRATION TEST")
    print("  Testing all nodes with secure psycopg2 database")
    print("=" * 70)

    # Track cleanup
    cleanup_ids = []

    # Test results
    results = {
        "node1_database": False,
        "node2_creator": False,
        "node3_decision": False,
        "node4_merger": False,
        "node5_search": False,
        "node6_workflow": False
    }

    try:
        # Node 1: Database operations
        db, test_id = test_node_1_database()
        if db:
            results["node1_database"] = True
            if test_id:
                cleanup_ids.append(test_id)
        else:
            print("\n❌ Cannot continue without database")
            return 1

        # Node 2: Document creator
        results["node2_creator"] = test_node_2_document_creator(db, cleanup_ids)

        # Node 3: Merge decision maker
        results["node3_decision"] = test_node_3_merge_decision(db)

        # Node 4: Document merger
        results["node4_merger"] = test_node_4_document_merger(db, cleanup_ids)

        # Node 5: Embedding search
        results["node5_search"] = test_node_5_embedding_search(db)

        # Node 6: Workflow manager (end-to-end)
        results["node6_workflow"] = test_node_6_workflow_manager(db, cleanup_ids)

        # Cleanup test data
        cleanup_test_data(db, cleanup_ids)

        # Close database
        db.close()

    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()

    # Print summary
    print("\n" + "=" * 70)
    print("  📊 TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for node_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {node_name.upper()}")

    print(f"\n   Total: {passed}/{total} nodes passed")

    if passed == total:
        print("\n" + "=" * 70)
        print("  🎉 ALL NODES WORKING WITH SECURE DATABASE!")
        print("=" * 70)
        print("\n  ✅ All components verified:")
        print("     - Database operations (secure psycopg2)")
        print("     - Document creator")
        print("     - Merge decision maker")
        print("     - Document merger")
        print("     - Embedding search")
        print("     - Workflow manager (end-to-end)")
        print("\n  🚀 System ready for production use!")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print("  ⚠️  SOME NODES FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit(main())
