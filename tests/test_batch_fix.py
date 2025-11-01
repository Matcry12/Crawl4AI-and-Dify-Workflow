#!/usr/bin/env python3
"""
Quick test to verify batch embedding format fix
"""

import os
os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', 'AIzaSyBlk1Pc88ZxhrtTHtU__rd2fwNcWw3ea-E')

from document_creator import DocumentCreator
from chunked_document_database import SimpleDocumentDatabase

def test_embedding_format():
    """Test that embeddings are returned in correct format (flat list, not nested)"""
    print("=" * 70)
    print("🧪 TESTING BATCH EMBEDDING FORMAT FIX")
    print("=" * 70)

    db = SimpleDocumentDatabase()
    creator = DocumentCreator(db)

    # Test with multiple texts
    test_texts = [
        "First test text",
        "Second test text",
        "Third test text"
    ]

    print(f"\n📝 Testing batch embedding with {len(test_texts)} texts...")

    try:
        embeddings = creator.create_embeddings_batch(test_texts)

        print(f"\n✅ Batch returned {len(embeddings)} embeddings")

        # Check format
        for i, emb in enumerate(embeddings):
            if not isinstance(emb, list):
                print(f"   ❌ Embedding {i} is not a list: {type(emb)}")
                return False

            if len(emb) == 0:
                print(f"   ❌ Embedding {i} is empty")
                return False

            # Check for nested arrays (the bug we're fixing)
            if isinstance(emb[0], list):
                print(f"   ❌ Embedding {i} is NESTED (wrong format): [[...]]")
                print(f"      First element type: {type(emb[0])}")
                print(f"      First few elements: {emb[:3]}")
                return False

            # Check for correct float values
            if not isinstance(emb[0], (float, int)):
                print(f"   ❌ Embedding {i} contains wrong type: {type(emb[0])}")
                return False

            print(f"   ✅ Embedding {i}: {len(emb)} dimensions, type: {type(emb[0])}")

        print(f"\n✅ All embeddings have correct format (flat lists of floats)")

        # Test document creation to ensure it works end-to-end
        print(f"\n📝 Testing document creation with batch embeddings...")

        test_topic = {
            "title": "Batch Format Test Document",
            "summary": "Testing that batch embeddings work correctly",
            "content": "This document tests the batch embedding format fix. " * 50,  # Long enough for multiple chunks
            "category": "test"
        }

        doc = creator.create_document(test_topic)

        if not doc:
            print(f"   ❌ Document creation failed")
            return False

        print(f"   ✅ Document created: {doc['id']}")
        print(f"   ✅ Chunks: {len(doc.get('chunks', []))}")

        # Verify chunks have proper embeddings
        for i, chunk in enumerate(doc.get('chunks', [])):
            emb = chunk.get('embedding')
            if not emb:
                print(f"   ❌ Chunk {i} missing embedding")
                return False

            if not isinstance(emb, list):
                print(f"   ❌ Chunk {i} embedding not a list: {type(emb)}")
                return False

            if isinstance(emb[0], list):
                print(f"   ❌ Chunk {i} embedding is NESTED (bug not fixed)")
                return False

            print(f"   ✅ Chunk {i}: {len(emb)} dimensions, correct format")

        # Clean up
        try:
            db._execute_query("DELETE FROM chunks WHERE document_id = %s", (doc['id'],), fetch=False)
            db._execute_query("DELETE FROM documents WHERE id = %s", (doc['id'],), fetch=False)
            print(f"\n   🧹 Test document cleaned up")
        except:
            pass

        print(f"\n" + "=" * 70)
        print(f"🎉 ALL TESTS PASSED - Batch embedding format is correct!")
        print(f"=" * 70)
        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_embedding_format()
    exit(0 if success else 1)
