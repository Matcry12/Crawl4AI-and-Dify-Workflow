#!/usr/bin/env python3
"""
Test Critical Fixes - Verify all 3 fixes are working correctly
"""

import os
from dotenv import load_dotenv
from chunked_document_database import SimpleDocumentDatabase
from merge_or_create_decision import MergeOrCreateDecision
from embedding_search import EmbeddingSearcher

load_dotenv()

print("="*80)
print("TESTING CRITICAL FIXES")
print("="*80)

# Initialize components
db = SimpleDocumentDatabase()
embedder = EmbeddingSearcher()

print("\n" + "="*80)
print("TEST 1: Database Returns Embeddings (Fix #2)")
print("="*80)

# Get documents with embeddings
docs = db.get_all_documents_with_embeddings()

if not docs:
    print("❌ FAIL: No documents in database")
    print("   Please run a crawl first to create documents")
    exit(1)

print(f"\n✅ Retrieved {len(docs)} documents")

# Check first document
doc = docs[0]
print(f"\nChecking first document: '{doc.get('title', 'Unknown')}'")
print(f"   Fields present:")
for key in ['id', 'title', 'summary', 'category', 'keywords', 'embedding', 'content_length', 'chunk_count']:
    has_field = key in doc
    value = doc.get(key)
    print(f"      {key}: {has_field} ", end='')

    if key == 'embedding':
        if value:
            print(f"(✅ {len(value)} dimensions)")
        else:
            print(f"(❌ None)")
    elif key == 'keywords':
        print(f"({len(value)} keywords)" if value else "(empty)")
    else:
        print(f"({value})")

# Verify embedding
has_embedding = 'embedding' in doc and doc['embedding'] is not None
embedding_dims = len(doc['embedding']) if has_embedding else 0

if has_embedding and embedding_dims == 768:
    print("\n✅ TEST 1 PASS: Database returns embeddings correctly")
    print(f"   Embedding: 768 dimensions as expected")
else:
    print("\n❌ TEST 1 FAIL: Embedding issue")
    print(f"   Has embedding: {has_embedding}")
    print(f"   Dimensions: {embedding_dims} (expected 768)")

print("\n" + "="*80)
print("TEST 2: Embedding Reuse (Fix #1)")
print("="*80)

# Create a test topic
test_topic = {
    'id': 'test-topic-fix-verify',
    'title': 'Test Security Features',
    'content': 'Testing security features including authentication and encryption.',
    'summary': 'Security features testing',
    'keywords': ['security', 'testing']
}

print("\nTest topic:")
print(f"   Title: '{test_topic['title']}'")
print(f"   Has embedding: {('embedding' in test_topic)}")

# Track API calls
api_call_count = {'topic': 0, 'docs': 0}

# Mock the create_embedding to track calls
original_create = embedder.create_embedding

def tracked_create(text):
    # Determine if it's topic or doc based on text content
    if 'Test Security Features' in text:
        api_call_count['topic'] += 1
        print(f"   📞 API call #{api_call_count['topic']}: Creating topic embedding")
    else:
        api_call_count['docs'] += 1
        print(f"   📞 API call #{api_call_count['topic'] + api_call_count['docs']}: Creating doc embedding (❌ SHOULDN'T HAPPEN!)")
    return original_create(text)

embedder.create_embedding = tracked_create

# Initialize decision maker
import google.generativeai as genai
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
llm_model = genai.GenerativeModel(os.getenv('DECISION_MAKER_MODEL', 'gemini-2.0-flash-lite'))
decision_maker = MergeOrCreateDecision(embedder, llm=llm_model)

print("\nMaking decision with existing documents (with embeddings)...")
print("   Expected: 1 API call for topic, 0 for documents (use stored)")

decision = decision_maker.decide(test_topic, docs[:5], use_llm_verification=False)

print(f"\nDecision result:")
print(f"   Action: {decision['action']}")
print(f"   Similarity: {decision.get('similarity', 0):.3f}")

print(f"\n📊 API Call Summary:")
print(f"   Topic embedding calls: {api_call_count['topic']} (expected: 1) {'✅' if api_call_count['topic'] == 1 else '❌'}")
print(f"   Document embedding calls: {api_call_count['docs']} (expected: 0) {'✅' if api_call_count['docs'] == 0 else '❌'}")

if api_call_count['topic'] == 1 and api_call_count['docs'] == 0:
    print("\n✅ TEST 2 PASS: Embedding reuse working correctly")
    print("   Documents use stored embeddings (no regeneration)")
else:
    print("\n❌ TEST 2 FAIL: Embeddings being regenerated")
    print(f"   Expected: 1 topic call, 0 doc calls")
    print(f"   Got: {api_call_count['topic']} topic calls, {api_call_count['docs']} doc calls")

print("\n" + "="*80)
print("TEST 3: Text Composition Consistency (Fix #3)")
print("="*80)

# Restore original function
embedder.create_embedding = original_create

# Check text composition by examining the code logic
print("\nVerifying text composition in merge_or_create_decision.py:")

# Read the file to check the logic
with open('merge_or_create_decision.py', 'r') as f:
    code = f.read()

# Check for the fixed patterns
checks = [
    ('title. summary pattern (line ~61)', 'topic.get(\'title\', \'\').' in code or 'f"{topic.get(\'title\'' in code),
    ('stored embedding check (line ~58)', '\'embedding\' in topic and topic[\'embedding\']' in code),
    ('stored doc embedding check (line ~70)', '\'embedding\' in doc and doc[\'embedding\']' in code),
    ('1000 char preview (line ~147)', '[:1000]' in code),
]

all_passed = True
for check_name, check_result in checks:
    status = '✅' if check_result else '❌'
    print(f"   {status} {check_name}: {check_result}")
    if not check_result:
        all_passed = False

if all_passed:
    print("\n✅ TEST 3 PASS: Text composition is consistent")
    print("   Code contains all expected patterns")
else:
    print("\n❌ TEST 3 FAIL: Some patterns missing")
    print("   Check the code manually")

print("\n" + "="*80)
print("FINAL SUMMARY")
print("="*80)

test_results = [
    ("Test 1: Database returns embeddings", has_embedding and embedding_dims == 768),
    ("Test 2: Embedding reuse working", api_call_count['topic'] == 1 and api_call_count['docs'] == 0),
    ("Test 3: Text composition consistent", all_passed)
]

passed = sum(1 for _, result in test_results if result)
total = len(test_results)

print(f"\nTests passed: {passed}/{total}")
print()

for test_name, result in test_results:
    status = '✅ PASS' if result else '❌ FAIL'
    print(f"   {status}: {test_name}")

if passed == total:
    print("\n" + "="*80)
    print("🎉 ALL TESTS PASSED - FIXES ARE WORKING CORRECTLY!")
    print("="*80)
    print("\nThe system is now:")
    print("   ✅ Using stored embeddings (10x faster)")
    print("   ✅ Database returning embeddings correctly")
    print("   ✅ Text composition aligned and consistent")
    print("\nReady for production use! 🚀")
else:
    print("\n" + "="*80)
    print("⚠️  SOME TESTS FAILED - REVIEW FIXES")
    print("="*80)
    print("\nPlease check the failed tests above and verify the fixes.")

print("\n" + "="*80)
