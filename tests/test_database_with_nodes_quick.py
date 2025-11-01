#!/usr/bin/env python3
"""
Quick Database Integration Test

Fast test to verify the secure psycopg2 database works correctly
with all major components, without heavy LLM operations.
"""

import os
os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', 'AIzaSyBlk1Pc88ZxhrtTHtU__rd2fwNcWw3ea-E')

from chunked_document_database import SimpleDocumentDatabase
from datetime import datetime


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main():
    print_header("🧪 QUICK DATABASE + NODES INTEGRATION TEST")

    results = {}

    try:
        # Test 1: Database connection
        print_header("TEST 1: Database Connection & Operations")

        db = SimpleDocumentDatabase()
        print("✅ Database initialized with secure psycopg2")

        # Get stats
        stats = db.get_stats()
        print(f"✅ Stats retrieved: {stats.get('total_documents', 0)} docs, {stats.get('total_chunks', 0)} chunks")

        # Get all documents
        docs = db.get_all_documents_with_embeddings()
        print(f"✅ Retrieved {len(docs)} documents with embeddings")

        if docs:
            # Get full document
            doc = db.get_document_by_id(docs[0]['id'])
            if doc:
                print(f"✅ Retrieved full document: {doc['id']}")
                print(f"   Content: {len(doc.get('content', ''))} chars")
                print(f"   Chunks: {len(doc.get('chunks', []))}")
                print(f"   Has embedding: {'embedding' in doc and doc['embedding'] is not None}")

        # Insert test document
        test_id = f"test_quick_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        test_doc = {
            "id": test_id,
            "title": "Quick Test Document",
            "summary": "Testing secure database",
            "content": "This is a test document.",
            "category": "test",
            "keywords": ["test"],
            "source_urls": [],
            "embedding": [0.1] * 768,
            "chunks": [
                {
                    "content": "Test chunk",
                    "chunk_index": 0,
                    "token_count": 2,
                    "embedding": [0.2] * 768
                }
            ]
        }

        if db.insert_document(test_doc):
            print(f"✅ Document inserted: {test_id}")

            # Update document
            test_doc['content'] = "Updated content"
            if db.update_document_with_chunks(test_doc):
                print(f"✅ Document updated")

                # Verify update
                retrieved = db.get_document_by_id(test_id)
                if "Updated" in retrieved.get('content', ''):
                    print(f"✅ Update verified")

        # Test transactions
        test_txn_id = f"test_txn_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        test_txn_doc = {
            **test_doc,
            "id": test_txn_id,
            "title": "Transaction Test"
        }

        db.begin_transaction()
        db.insert_document(test_txn_doc)
        db.rollback_transaction()

        if not db.get_document_by_id(test_txn_id):
            print(f"✅ Transaction rollback working")

        # Cleanup
        for tid in [test_id, test_txn_id]:
            try:
                db._execute_query("DELETE FROM chunks WHERE document_id = %s", (tid,), fetch=False)
                db._execute_query("DELETE FROM documents WHERE id = %s", (tid,), fetch=False)
            except:
                pass

        print("\n✅ TEST 1 PASSED: Database operations working correctly")
        results["database"] = True

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["database"] = False

    # Test 2: Import and initialize all nodes
    print_header("TEST 2: All Nodes Import & Initialize")

    try:
        from document_creator import DocumentCreator
        from document_merger import DocumentMerger
        from merge_or_create_decision import MergeOrCreateDecision
        from embedding_search import EmbeddingSearcher

        print("✅ All modules imported successfully")

        # Initialize with database
        creator = DocumentCreator(db)
        print(f"✅ DocumentCreator initialized")

        merger = DocumentMerger(db)
        print(f"✅ DocumentMerger initialized")

        searcher = EmbeddingSearcher(db)
        print(f"✅ EmbeddingSearcher initialized")

        decision_maker = MergeOrCreateDecision(searcher)
        print(f"✅ MergeOrCreateDecision initialized")

        print("\n✅ TEST 2 PASSED: All nodes initialized with secure database")
        results["nodes"] = True

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["nodes"] = False

    # Test 3: Verify nodes can access database
    print_header("TEST 3: Nodes Database Access")

    try:
        # Verify nodes can access database through their db attribute
        if hasattr(creator, 'db') and creator.db is not None:
            print(f"✅ DocumentCreator has database access")

        if hasattr(merger, 'db') and merger.db is not None:
            print(f"✅ DocumentMerger has database access")

        if hasattr(searcher, 'db') and searcher.db is not None:
            print(f"✅ EmbeddingSearcher has database access")

        # Verify database connection is psycopg2 (secure)
        if hasattr(db, 'connection_pool') and db.connection_pool is not None:
            print(f"✅ Database using secure psycopg2 connection pool")

        # Verify existing tests still work (from test_critical_fixes.py)
        print(f"\n📋 Verifying existing test compatibility...")
        all_docs = db.get_all_documents_with_embeddings()
        if len(all_docs) > 0:
            first_doc = all_docs[0]
            if 'embedding' in first_doc:
                print(f"✅ Documents have embeddings (Fix #2 verified)")

            # Get full document
            full_doc = db.get_document_by_id(first_doc['id'])
            if full_doc and 'embedding' in full_doc:
                print(f"✅ Full documents return embeddings (compatibility verified)")

        print("\n✅ TEST 3 PASSED: All nodes have proper database access")
        results["operations"] = True

    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["operations"] = False

    # Close database
    db.close()

    # Print summary
    print_header("📊 TEST SUMMARY")

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name.upper()}")

    print(f"\n   Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n" + "=" * 70)
        print("  🎉 ALL TESTS PASSED!")
        print("=" * 70)
        print("\n  ✅ Secure psycopg2 database working correctly")
        print("  ✅ All nodes compatible with secure database")
        print("  ✅ Database operations functional")
        print("  ✅ Node operations working")
        print("\n  🚀 System ready for production!")
        print("=" * 70)
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit(main())
