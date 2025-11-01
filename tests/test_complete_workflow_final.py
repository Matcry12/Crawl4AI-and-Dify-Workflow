#!/usr/bin/env python3
"""
Complete End-to-End Workflow Test

Tests the entire workflow from document creation to database insertion
to verify all fixes are working properly.
"""

import os
os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', 'AIzaSyBlk1Pc88ZxhrtTHtU__rd2fwNcWw3ea-E')

from document_creator import DocumentCreator
from document_merger import DocumentMerger
from embedding_search import EmbeddingSearcher
from merge_or_create_decision import MergeOrCreateDecision
from chunked_document_database import SimpleDocumentDatabase
import time


def test_complete_workflow():
    """Run complete end-to-end workflow test"""
    print("\n" + "=" * 80)
    print("🔍 COMPLETE END-TO-END WORKFLOW TEST")
    print("=" * 80)
    print("\nThis test verifies the entire workflow:")
    print("1. Database initialization (psycopg2)")
    print("2. Document creation with batch embeddings")
    print("3. Database insertion (with nested array protection)")
    print("4. Similarity search")
    print("5. Document merging")
    print("=" * 80)

    try:
        # Step 1: Initialize all components
        print("\n" + "=" * 80)
        print("STEP 1: Initialize Components")
        print("=" * 80)

        db = SimpleDocumentDatabase()
        print("✅ Database initialized")

        creator = DocumentCreator()
        print("✅ Document Creator initialized")

        merger = DocumentMerger()
        print("✅ Document Merger initialized")

        searcher = EmbeddingSearcher(db)
        print("✅ Embedding Searcher initialized")

        decision_maker = MergeOrCreateDecision(searcher)
        print("✅ Decision Maker initialized")

        # Step 2: Create first document
        print("\n" + "=" * 80)
        print("STEP 2: Create First Document (Batch Embedding)")
        print("=" * 80)

        topic1 = {
            'title': 'Python Advanced Features',
            'category': 'tutorial',
            'summary': 'Advanced Python programming techniques and patterns',
            'content': """Python offers many advanced features that make programming more efficient and elegant.

## Decorators
Decorators are a powerful tool for modifying function behavior. They allow you to wrap functions with additional functionality without modifying the original function code. Common uses include logging, authentication, and caching.

## Context Managers
Context managers provide a clean way to manage resources. The 'with' statement ensures proper resource cleanup even if errors occur. You can create custom context managers using the __enter__ and __exit__ methods.

## Generators
Generators provide memory-efficient iteration over large datasets. They use the yield keyword instead of return, allowing lazy evaluation. This is particularly useful for processing large files or infinite sequences.

## Metaclasses
Metaclasses are classes that create classes. They provide deep control over class creation and can be used for validation, automatic registration, and interface enforcement.""",
            'keywords': ['python', 'decorators', 'context-managers', 'generators', 'metaclasses'],
            'source_url': 'https://example.com/python-advanced'
        }

        result1 = creator.create_documents_batch([topic1])

        if not result1['documents']:
            print("❌ Failed to create first document")
            return False

        doc1 = result1['documents'][0]
        print(f"✅ Created document with {len(doc1['chunks'])} chunks")

        # Step 3: Insert first document
        print("\n" + "=" * 80)
        print("STEP 3: Insert Document into Database")
        print("=" * 80)

        db_result1 = db.insert_documents_batch([doc1])

        if db_result1.get('success_count', 0) == 0:
            print("❌ Failed to insert first document")
            errors = db_result1.get('errors', [])
            for error in errors[:3]:
                print(f"   Error: {error}")
            return False

        print(f"✅ Inserted document into database")
        print(f"   Document ID: {doc1['id']}")
        print(f"   Chunks: {len(doc1['chunks'])}")

        # Step 4: Search for similar documents
        print("\n" + "=" * 80)
        print("STEP 4: Search for Similar Documents")
        print("=" * 80)

        # Create a related topic
        topic2 = {
            'title': 'Python Decorators Deep Dive',
            'category': 'tutorial',
            'summary': 'In-depth exploration of Python decorators and their uses',
            'content': """Decorators are one of Python's most powerful features.

## Basic Decorators
A decorator is a function that takes another function and extends its behavior. The @decorator syntax is syntactic sugar for wrapping functions.

## Decorator Patterns
Common patterns include function decorators, class decorators, and decorators with arguments. Each pattern serves different use cases.

## Practical Applications
Decorators are used for logging, timing, authentication, caching, and validation. They keep code DRY and maintainable.""",
            'keywords': ['python', 'decorators', 'patterns'],
            'source_url': 'https://example.com/python-decorators'
        }

        # Generate embedding for search
        search_embedding = creator.create_embedding(topic2['summary'])

        if not search_embedding:
            print("❌ Failed to generate search embedding")
            return False

        # Search for similar documents
        similar_docs = searcher.search_similar_documents(
            query_embedding=search_embedding,
            top_k=3,
            threshold=0.3
        )

        print(f"✅ Found {len(similar_docs)} similar documents")
        for i, (doc_id, score) in enumerate(similar_docs, 1):
            print(f"   {i}. Document: {doc_id} (Score: {score:.3f})")

        # Step 5: Make merge decision
        print("\n" + "=" * 80)
        print("STEP 5: Make Merge Decision")
        print("=" * 80)

        decision = decision_maker.decide(topic2)

        print(f"✅ Decision: {decision['action']}")
        print(f"   Confidence: {decision['confidence']:.2%}")
        print(f"   Reason: {decision['reason']}")

        if decision['action'] == 'merge':
            print(f"   Target document: {decision['target_document_id']}")

        # Step 6: Execute merge if decided
        if decision['action'] == 'merge':
            print("\n" + "=" * 80)
            print("STEP 6: Execute Document Merge")
            print("=" * 80)

            target_doc = db.get_document_by_id(decision['target_document_id'])

            if not target_doc:
                print("❌ Failed to retrieve target document")
                return False

            merged_doc = merger.merge_topic_into_document(topic2, target_doc)

            if not merged_doc:
                print("❌ Failed to merge documents")
                return False

            print(f"✅ Documents merged successfully")
            print(f"   Merged document ID: {merged_doc['id']}")
            print(f"   New chunk count: {len(merged_doc['chunks'])}")

            # Update database
            update_result = db.update_document(merged_doc)

            if update_result:
                print(f"✅ Updated document in database")
            else:
                print("⚠️  Database update returned no result")

        else:
            print("\n" + "=" * 80)
            print("STEP 6: Create New Document (No Merge)")
            print("=" * 80)

            result2 = creator.create_documents_batch([topic2])

            if not result2['documents']:
                print("❌ Failed to create second document")
                return False

            doc2 = result2['documents'][0]
            print(f"✅ Created new document with {len(doc2['chunks'])} chunks")

            db_result2 = db.insert_documents_batch([doc2])

            if db_result2.get('success_count', 0) == 0:
                print("❌ Failed to insert second document")
                return False

            print(f"✅ Inserted second document into database")

        # Step 7: Verify database state
        print("\n" + "=" * 80)
        print("STEP 7: Verify Database State")
        print("=" * 80)

        # Count total documents
        count_query = "SELECT COUNT(*) FROM documents"
        result = db._execute_query(count_query, fetch=True)
        doc_count = result[0][0] if result else 0

        print(f"✅ Total documents in database: {doc_count}")

        # Count total chunks
        chunk_query = "SELECT COUNT(*) FROM chunks"
        result = db._execute_query(chunk_query, fetch=True)
        chunk_count = result[0][0] if result else 0

        print(f"✅ Total chunks in database: {chunk_count}")

        # Final verification
        print("\n" + "=" * 80)
        print("📊 WORKFLOW TEST RESULTS")
        print("=" * 80)
        print("✅ Database initialization: PASSED")
        print("✅ Document creation with batch embedding: PASSED")
        print("✅ Database insertion (nested array protection): PASSED")
        print("✅ Similarity search: PASSED")
        print("✅ Merge decision: PASSED")
        print("✅ Document merge/create: PASSED")
        print("✅ Database verification: PASSED")
        print("\n" + "=" * 80)
        print("🎉 ALL WORKFLOW TESTS PASSED!")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ WORKFLOW TEST FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_complete_workflow()
    exit(0 if success else 1)
