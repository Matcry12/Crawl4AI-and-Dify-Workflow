#!/usr/bin/env python3
"""
Test to diagnose batch embedding parsing bug

Simulates different response formats from Gemini API to find the parsing issue.
"""

def simulate_parsing(result_format_name, result_data):
    """Simulate the parsing logic with different response formats"""

    print(f"\n{'='*80}")
    print(f"Testing: {result_format_name}")
    print(f"{'='*80}")

    all_embeddings = []

    # Simulate the result object
    class MockResult:
        pass

    result = MockResult()

    # Set up the mock result based on format
    if 'embedding' in result_data:
        result.embedding = result_data['embedding']
    if 'embeddings' in result_data:
        result.embeddings = result_data['embeddings']

    # THIS IS THE ACTUAL PARSING LOGIC FROM THE CODE
    if hasattr(result, 'embedding'):
        # Single embedding via attribute (batch of 1)
        emb = result.embedding
        print(f"  Found result.embedding")
        print(f"  Type: {type(emb)}")
        print(f"  Length: {len(emb) if isinstance(emb, list) else 'N/A'}")

        if isinstance(emb, list) and len(emb) > 0:
            print(f"  emb[0] type: {type(emb[0])}")
            if isinstance(emb[0], list):
                print(f"  emb[0] length: {len(emb[0])}")

        if isinstance(emb, list) and len(emb) > 0 and isinstance(emb[0], list):
            # Already nested: [[...]]
            print(f"  → Using extend (nested case)")
            all_embeddings.extend(emb)
        else:
            # Flat: [...]
            print(f"  → Using append (flat case)")
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

    print(f"\n  Result: {len(all_embeddings)} embeddings extracted")
    print(f"  all_embeddings structure:")
    for i, emb in enumerate(all_embeddings[:3]):  # Show first 3
        if isinstance(emb, list):
            if len(emb) > 0 and isinstance(emb[0], list):
                print(f"    [{i}]: NESTED list, len={len(emb)}, first item len={len(emb[0])}")
            else:
                print(f"    [{i}]: FLAT list, len={len(emb)}")
        else:
            print(f"    [{i}]: {type(emb)}")

    return all_embeddings


# Test different response formats
print("\n" + "="*80)
print("BATCH EMBEDDING PARSING BUG DIAGNOSIS")
print("="*80)
print("\nTesting 5 chunks sent to batch API...")

# Simulate 5 embeddings (simplified as short lists)
emb1 = [0.1, 0.2, 0.3]  # In reality these are 768 floats
emb2 = [0.4, 0.5, 0.6]
emb3 = [0.7, 0.8, 0.9]
emb4 = [1.0, 1.1, 1.2]
emb5 = [1.3, 1.4, 1.5]

# Test Format 1: result.embedding contains all 5 in a list
print("\n" + "="*80)
print("SCENARIO 1: result.embedding = [emb1, emb2, emb3, emb4, emb5]")
print("="*80)
result1 = simulate_parsing(
    "Format 1: Flat list in result.embedding",
    {'embedding': [emb1, emb2, emb3, emb4, emb5]}
)

# Test Format 2: result.embedding contains nested structure
print("\n" + "="*80)
print("SCENARIO 2: result.embedding = [[emb1, emb2, emb3, emb4, emb5]]")
print("="*80)
result2 = simulate_parsing(
    "Format 2: Double-nested in result.embedding",
    {'embedding': [[emb1, emb2, emb3, emb4, emb5]]}
)

# Test Format 3: result.embeddings (plural) contains list
print("\n" + "="*80)
print("SCENARIO 3: result.embeddings = [emb1, emb2, emb3, emb4, emb5]")
print("="*80)
result3 = simulate_parsing(
    "Format 3: List in result.embeddings",
    {'embeddings': [emb1, emb2, emb3, emb4, emb5]}
)

# Test Format 4: result.embedding as nested arrays
print("\n" + "="*80)
print("SCENARIO 4: result.embedding = [[emb1], [emb2], [emb3], [emb4], [emb5]]")
print("="*80)
result4 = simulate_parsing(
    "Format 4: Individually nested in result.embedding",
    {'embedding': [[emb1], [emb2], [emb3], [emb4], [emb5]]}
)

# Summary
print("\n" + "="*80)
print("SUMMARY: Which format gives us 5 embeddings?")
print("="*80)
print(f"Format 1 (flat in .embedding):            {len(result1)} embeddings ❌" if len(result1) != 5 else f"Format 1: {len(result1)} embeddings ✅")
print(f"Format 2 (double-nested in .embedding):   {len(result2)} embeddings ❌" if len(result2) != 5 else f"Format 2: {len(result2)} embeddings ✅")
print(f"Format 3 (list in .embeddings):           {len(result3)} embeddings ❌" if len(result3) != 5 else f"Format 3: {len(result3)} embeddings ✅")
print(f"Format 4 (individually nested):           {len(result4)} embeddings ❌" if len(result4) != 5 else f"Format 4: {len(result4)} embeddings ✅")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

if len(result1) == 1:
    print("\n⚠️  BUG FOUND in Format 1!")
    print("   When result.embedding = [emb1, emb2, emb3, emb4, emb5]")
    print("   The code treats this as a SINGLE flat embedding")
    print("   Because emb[0]=emb1=[0.1,0.2,0.3] which IS a list")
    print("   So isinstance(emb[0], list) = True")
    print("   But the code does extend() which adds [emb1,emb2,emb3,emb4,emb5] as ONE item")
    print("   Result: Only 1 'embedding' in chunk_embeddings")
    print("   This is the bug causing 1/5 chunks to get embeddings!")

if len(result2) == 1:
    print("\n⚠️  BUG FOUND in Format 2!")
    print("   When result.embedding = [[emb1, emb2, emb3, emb4, emb5]]")
    print("   The code does extend() which adds the outer list")
    print("   Result: Only 1 'embedding' (containing all 5)")

print("\n" + "="*80)
