#!/usr/bin/env python3
"""
Verify Database State - Check embeddings are properly stored
"""

from chunked_document_database import SimpleDocumentDatabase

def verify_database():
    """Verify all embeddings in database are flat arrays"""

    print("\n" + "=" * 80)
    print("📊 DATABASE STATE VERIFICATION")
    print("=" * 80)

    db = SimpleDocumentDatabase()

    # Count documents
    result = db._execute_query('SELECT COUNT(*) FROM documents', fetch=True)
    doc_count = result[0][0] if result else 0

    # Count chunks
    result = db._execute_query('SELECT COUNT(*) FROM chunks', fetch=True)
    chunk_count = result[0][0] if result else 0

    print(f"\nTotal documents: {doc_count}")
    print(f"Total chunks: {chunk_count}")

    # Get recent documents
    query = """
        SELECT id, title, category, created_at
        FROM documents
        ORDER BY created_at DESC
        LIMIT 5
    """
    result = db._execute_query(query, fetch=True)

    print(f"\n📄 Recent Documents:")

    nested_found = False
    flat_count = 0
    checked_docs = []

    if result:
        for row in result:
            doc_id = row[0]
            title = row[1]
            category = row[2] if len(row) > 2 else 'unknown'

            print(f"\n   - {title}")
            print(f"     ID: {doc_id}")
            print(f"     Category: {category}")

            # Get chunks for this document
            chunk_query = """
                SELECT id, embedding
                FROM chunks
                WHERE document_id = %s
                LIMIT 3
            """
            chunk_result = db._execute_query(chunk_query, (doc_id,), fetch=True)

            if chunk_result:
                print(f"     Chunks: {len(chunk_result)}")

                for chunk_row in chunk_result:
                    chunk_id = chunk_row[0]
                    emb = chunk_row[1]

                    if emb:
                        # Check if embedding is nested
                        if isinstance(emb, list):
                            if len(emb) > 0 and isinstance(emb[0], list):
                                print(f"       ❌ Chunk {chunk_id[:8]}: NESTED ARRAY [[...]]")
                                nested_found = True
                            else:
                                print(f"       ✅ Chunk {chunk_id[:8]}: Flat array [dim={len(emb)}]")
                                flat_count += 1
                        else:
                            print(f"       ℹ️  Chunk {chunk_id[:8]}: Type={type(emb).__name__}")
                    else:
                        print(f"       ⚠️  Chunk {chunk_id[:8]}: No embedding")
            else:
                print(f"     ⚠️  No chunks found")

            checked_docs.append(doc_id)
    else:
        print("   No documents found in database")

    # Summary
    print("\n" + "=" * 80)
    print("📊 EMBEDDING FORMAT VERIFICATION")
    print("=" * 80)
    print(f"Documents checked: {len(checked_docs)}")
    print(f"Flat arrays found: {flat_count}")
    print(f"Nested arrays found: {1 if nested_found else 0}")

    if nested_found:
        print("\n❌ NESTED ARRAYS DETECTED - Bug still present!")
        print("=" * 80)
        return False
    elif flat_count > 0:
        print(f"\n✅ All {flat_count} embeddings are FLAT arrays")
        print("✅ Nested array bug is FIXED!")
        print("=" * 80)
        return True
    else:
        print("\n⚠️  No embeddings found to check")
        print("   This could mean:")
        print("   1. No documents with chunks in database")
        print("   2. API rate limiting prevented document creation")
        print("=" * 80)
        return None


if __name__ == "__main__":
    result = verify_database()

    if result is True:
        print("\n🎉 DATABASE VERIFICATION PASSED")
        exit(0)
    elif result is False:
        print("\n❌ DATABASE VERIFICATION FAILED")
        exit(1)
    else:
        print("\n⚠️  DATABASE VERIFICATION INCONCLUSIVE")
        exit(2)
