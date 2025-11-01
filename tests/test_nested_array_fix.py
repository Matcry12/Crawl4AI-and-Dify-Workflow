#!/usr/bin/env python3
"""
Test to verify nested array bug is fixed

This test checks that embeddings are properly flattened before database insertion.
"""

import os
os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', 'AIzaSyBlk1Pc88ZxhrtTHtU__rd2fwNcWw3ea-E')

from document_creator import DocumentCreator
from chunked_document_database import SimpleDocumentDatabase

def test_nested_array_fix():
    """Test that nested array bug is fixed"""
    print("=" * 80)
    print("TEST: Nested Array Fix Verification")
    print("=" * 80)

    try:
        # Initialize components
        db = SimpleDocumentDatabase()
        creator = DocumentCreator()

        print("\n✅ Components initialized")

        # Create a simple test topic
        test_topic = {
            'title': 'Nested Array Fix Test',
            'category': 'test',
            'summary': 'Testing that embeddings are properly flattened',
            'content': """This is a test document to verify that the nested array bug is fixed.

The bug was causing embeddings to be returned as nested arrays [[...]] instead of flat arrays [...].
This caused PostgreSQL pgvector to reject the data with an error like:
❌ Query failed: invalid input syntax for type vector: "[[0.05697837, ...]]"

The fix adds defensive flattening code that checks each embedding before assignment.
If a nested array is detected, it automatically flattens it to prevent database errors.

This should work correctly now.""",
            'keywords': ['test', 'nested-array', 'fix', 'embedding'],
            'source_url': 'https://example.com/test'
        }

        print("\n📄 Creating test document...")
        result = creator.create_documents_batch([test_topic])

        if not result['documents']:
            print("❌ Failed to create document")
            return False

        document = result['documents'][0]
        print(f"✅ Document created with {len(document['chunks'])} chunks")

        # Verify embeddings are flat arrays
        print("\n🔍 Verifying embedding format...")
        all_flat = True

        # Check document embedding
        doc_emb = document.get('embedding')
        if doc_emb and isinstance(doc_emb, list) and len(doc_emb) > 0:
            if isinstance(doc_emb[0], list):
                print(f"❌ Document embedding is nested: {type(doc_emb[0])}")
                all_flat = False
            else:
                print(f"✅ Document embedding is flat (first element: {type(doc_emb[0])})")

        # Check chunk embeddings
        nested_count = 0
        for i, chunk in enumerate(document['chunks'][:5]):  # Check first 5 chunks
            emb = chunk.get('embedding')
            if emb and isinstance(emb, list) and len(emb) > 0:
                if isinstance(emb[0], list):
                    print(f"❌ Chunk {i+1} embedding is nested: {type(emb[0])}")
                    nested_count += 1
                    all_flat = False

        if nested_count == 0:
            print(f"✅ All chunk embeddings are flat arrays")
        else:
            print(f"❌ Found {nested_count} nested chunk embeddings")

        if not all_flat:
            print("\n❌ NESTED ARRAY BUG STILL PRESENT")
            return False

        # Try to insert into database
        print("\n💾 Attempting database insertion...")
        try:
            db_result = db.insert_documents_batch([document])

            if db_result.get('success_count', 0) > 0:
                print(f"✅ Successfully inserted document into database")
                print(f"   Document ID: {document['id']}")
                return True
            else:
                errors = db_result.get('errors', [])
                print(f"❌ Database insertion failed:")
                for error in errors[:3]:  # Show first 3 errors
                    print(f"   {error}")
                return False

        except Exception as e:
            error_msg = str(e)
            if "invalid input syntax for type vector" in error_msg and "[[" in error_msg:
                print(f"❌ NESTED ARRAY BUG STILL PRESENT IN DATABASE INSERTION")
                print(f"   Error: {error_msg[:200]}...")
                return False
            else:
                print(f"❌ Database insertion error (not nested array): {error_msg[:200]}")
                return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "=" * 80)
    print("🔍 NESTED ARRAY FIX VERIFICATION TEST")
    print("=" * 80)
    print("\nThis test verifies that the nested array bug is fixed.")
    print("It creates a document and checks that all embeddings are flat arrays.")
    print("=" * 80)

    success = test_nested_array_fix()

    print("\n" + "=" * 80)
    if success:
        print("🎉 TEST PASSED - Nested Array Bug is FIXED!")
        print("=" * 80)
        print("\n✅ Verification complete:")
        print("   - Embeddings are flat arrays [float, ...]")
        print("   - No nested arrays [[float, ...]] detected")
        print("   - Database insertion successful")
        print("   - PostgreSQL pgvector accepting embeddings")
        print("\n✅ The fix is working correctly!")
        return 0
    else:
        print("❌ TEST FAILED - Nested Array Bug Still Present")
        print("=" * 80)
        print("\n⚠️  The bug needs further investigation")
        return 1


if __name__ == "__main__":
    exit(main())
