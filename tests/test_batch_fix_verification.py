#!/usr/bin/env python3
"""
Verify the batch parsing fix works correctly
"""

def fixed_parsing(result_format_name, result_data, batch_size):
    """The FIXED parsing logic"""

    print(f"\n{'='*80}")
    print(f"Testing: {result_format_name}")
    print(f"{'='*80}")

    all_embeddings = []
    batch = [f"text{i}" for i in range(batch_size)]  # Simulate batch

    # Simulate the result object
    class MockResult:
        pass

    result = MockResult()

    # Set up the mock result based on format
    if 'embedding' in result_data:
        result.embedding = result_data['embedding']
    if 'embeddings' in result_data:
        result.embeddings = result_data['embeddings']

    # THIS IS THE FIXED PARSING LOGIC
    if hasattr(result, 'embedding'):
        emb = result.embedding
        print(f"  Found result.embedding (len={len(emb) if isinstance(emb, list) else 'N/A'})")

        if isinstance(emb, list) and len(emb) > 0 and isinstance(emb[0], list):
            # Nested structure detected
            # Check if it's double-nested: [[emb1, emb2, emb3, ...]] (all embeddings in one wrapper)
            if len(emb) == 1 and isinstance(emb[0], list) and len(emb[0]) == len(batch):
                # Double-nested case: [[emb1, emb2, ...]] where inner list has ALL embeddings
                print(f"  🔍 Detected double-nested format (len(emb)=1, len(emb[0])={len(emb[0])})")
                print(f"  → Flattening by extracting emb[0]")
                all_embeddings.extend(emb[0])  # Extract the inner list with all embeddings
            else:
                # Regular nested: [[emb1], [emb2], [emb3], ...] (each embedding wrapped separately)
                print(f"  → Regular nested format (len(emb)={len(emb)})")
                all_embeddings.extend(emb)
        else:
            # Flat: [...]
            print(f"  → Flat format")
            all_embeddings.append(emb)

    elif hasattr(result, 'embeddings'):
        print(f"  Found result.embeddings")
        for emb in result.embeddings:
            all_embeddings.append(emb)

    print(f"\n  ✅ Result: {len(all_embeddings)} embeddings extracted")
    return all_embeddings


# Test with the bug scenario
print("\n" + "="*80)
print("BATCH EMBEDDING FIX VERIFICATION")
print("="*80)
print("\nTesting the problematic Format 2 with FIX...")

# Simulate 5 embeddings
emb1 = [0.1, 0.2, 0.3]
emb2 = [0.4, 0.5, 0.6]
emb3 = [0.7, 0.8, 0.9]
emb4 = [1.0, 1.1, 1.2]
emb5 = [1.3, 1.4, 1.5]

# Test the problematic format
result = fixed_parsing(
    "Format 2: Double-nested [[emb1, emb2, emb3, emb4, emb5]]",
    {'embedding': [[emb1, emb2, emb3, emb4, emb5]]},
    batch_size=5
)

# Verify
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)

if len(result) == 5:
    print(f"✅ SUCCESS! Extracted all {len(result)} embeddings")
    print(f"   Embeddings: {[emb[:2] for emb in result]}")
    print("\n🎉 BUG IS FIXED!")
else:
    print(f"❌ FAILED! Only extracted {len(result)} embeddings (expected 5)")
    print("\n⚠️  Bug still present")

print("="*80)
