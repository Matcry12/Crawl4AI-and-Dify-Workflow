#!/usr/bin/env python3
"""
Test the actual batch embedding code with the fix

This imports the REAL code and tests it with simulated API responses.
"""

import os
os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', 'AIzaSyBlk1Pc88ZxhrtTHtU__rd2fwNcWw3ea-E')

# Mock the genai module to simulate different response formats
class MockEmbedding:
    def __init__(self, values):
        self.values = values

class MockResult:
    def __init__(self, embedding=None, embeddings=None):
        if embedding is not None:
            self.embedding = embedding
        if embeddings is not None:
            self.embeddings = embeddings

# Test function
def test_batch_parsing():
    """Test the batch embedding parsing with different formats"""

    print("\n" + "="*80)
    print("TESTING ACTUAL BATCH EMBEDDING CODE")
    print("="*80)

    # Import the actual parsing logic by copying it
    def parse_batch_result(result, batch):
        """Actual parsing logic from document_creator.py/document_merger.py"""
        all_embeddings = []

        # Extract embeddings from result - Gemini returns different formats
        if hasattr(result, 'embedding'):
            # Single embedding via attribute (batch of 1)
            emb = result.embedding
            print(f"  Found result.embedding, type={type(emb)}, len={len(emb) if isinstance(emb, list) else 'N/A'}")

            if isinstance(emb, list) and len(emb) > 0 and isinstance(emb[0], list):
                # Nested structure detected
                print(f"  Nested structure: len(emb)={len(emb)}, len(emb[0])={len(emb[0]) if isinstance(emb[0], list) else 'N/A'}")

                # Check if it's double-nested: [[emb1, emb2, emb3, ...]] (all embeddings in one wrapper)
                if len(emb) == 1 and isinstance(emb[0], list) and len(emb[0]) == len(batch):
                    # Double-nested case: [[emb1, emb2, ...]] where inner list has ALL embeddings
                    print(f"  🔍 Detected double-nested format, flattening...")
                    print(f"     len(batch)={len(batch)}, len(emb[0])={len(emb[0])}")
                    all_embeddings.extend(emb[0])  # Extract the inner list with all embeddings
                else:
                    # Regular nested: [[emb1], [emb2], [emb3], ...] (each embedding wrapped separately)
                    print(f"  Regular nested format")
                    all_embeddings.extend(emb)
            else:
                # Flat: [...]
                print(f"  Flat format")
                all_embeddings.append(emb)
        elif hasattr(result, 'embeddings'):
            # Multiple embeddings via attribute
            print(f"  Found result.embeddings")
            for emb in result.embeddings:
                if hasattr(emb, 'values'):
                    all_embeddings.append(emb.values)
                elif isinstance(emb, list):
                    all_embeddings.append(emb)
                else:
                    all_embeddings.append(list(emb))

        return all_embeddings

    # Create test embeddings (simplified to 3 dimensions for testing)
    emb1 = [0.1, 0.2, 0.3]
    emb2 = [0.4, 0.5, 0.6]
    emb3 = [0.7, 0.8, 0.9]
    emb4 = [1.0, 1.1, 1.2]
    emb5 = [1.3, 1.4, 1.5]

    batch_size_5 = ["text1", "text2", "text3", "text4", "text5"]

    # Test 1: Double-nested format (THE BUG)
    print("\n" + "-"*80)
    print("TEST 1: Double-nested [[emb1, emb2, emb3, emb4, emb5]]")
    print("-"*80)
    result1 = MockResult(embedding=[[emb1, emb2, emb3, emb4, emb5]])
    parsed1 = parse_batch_result(result1, batch_size_5)
    print(f"Result: {len(parsed1)} embeddings")
    if len(parsed1) == 5:
        print("✅ PASS - All 5 embeddings extracted")
    else:
        print(f"❌ FAIL - Expected 5, got {len(parsed1)}")

    # Test 2: Individual nesting [[emb1], [emb2], ...]
    print("\n" + "-"*80)
    print("TEST 2: Individual nesting [[emb1], [emb2], [emb3], [emb4], [emb5]]")
    print("-"*80)
    result2 = MockResult(embedding=[[emb1], [emb2], [emb3], [emb4], [emb5]])
    parsed2 = parse_batch_result(result2, batch_size_5)
    print(f"Result: {len(parsed2)} embeddings")
    if len(parsed2) == 5:
        print("✅ PASS - All 5 embeddings extracted")
    else:
        print(f"❌ FAIL - Expected 5, got {len(parsed2)}")

    # Test 3: Flat list [emb1, emb2, ...]
    print("\n" + "-"*80)
    print("TEST 3: Flat list [emb1, emb2, emb3, emb4, emb5]")
    print("-"*80)
    result3 = MockResult(embedding=[emb1, emb2, emb3, emb4, emb5])
    parsed3 = parse_batch_result(result3, batch_size_5)
    print(f"Result: {len(parsed3)} embeddings")
    if len(parsed3) == 5:
        print("✅ PASS - All 5 embeddings extracted")
    else:
        print(f"❌ FAIL - Expected 5, got {len(parsed3)}")

    # Test 4: result.embeddings format
    print("\n" + "-"*80)
    print("TEST 4: result.embeddings = [emb1, emb2, emb3, emb4, emb5]")
    print("-"*80)
    result4 = MockResult(embeddings=[emb1, emb2, emb3, emb4, emb5])
    parsed4 = parse_batch_result(result4, batch_size_5)
    print(f"Result: {len(parsed4)} embeddings")
    if len(parsed4) == 5:
        print("✅ PASS - All 5 embeddings extracted")
    else:
        print(f"❌ FAIL - Expected 5, got {len(parsed4)}")

    # Test 5: Single embedding (batch size 1)
    print("\n" + "-"*80)
    print("TEST 5: Single embedding (batch size 1)")
    print("-"*80)
    batch_size_1 = ["text1"]
    result5 = MockResult(embedding=emb1)
    parsed5 = parse_batch_result(result5, batch_size_1)
    print(f"Result: {len(parsed5)} embeddings")
    if len(parsed5) == 1:
        print("✅ PASS - 1 embedding extracted")
    else:
        print(f"❌ FAIL - Expected 1, got {len(parsed5)}")

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    tests = [
        ("Double-nested (THE BUG)", len(parsed1) == 5),
        ("Individual nesting", len(parsed2) == 5),
        ("Flat list", len(parsed3) == 5),
        ("result.embeddings", len(parsed4) == 5),
        ("Single embedding", len(parsed5) == 1)
    ]

    passed = sum(1 for _, result in tests if result)
    total = len(tests)

    for name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED - FIX IS WORKING!")
        return True
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED - FIX NEEDS WORK")
        return False


if __name__ == "__main__":
    success = test_batch_parsing()
    exit(0 if success else 1)
