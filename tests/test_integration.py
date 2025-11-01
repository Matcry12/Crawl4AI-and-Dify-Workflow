#!/usr/bin/env python3
"""
Integration Testing for Simplified RAG Workflow

Tests:
1. Simple quality chunker
2. Multi-signal merge decision
3. Document creation with chunks
4. Database save and retrieval
5. Document merge with re-chunking
6. Parent Document Retrieval
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import List, Dict

# Test configuration
TEST_MODE = True
os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', '')

if not os.environ['GEMINI_API_KEY']:
    print("❌ GEMINI_API_KEY not set in .env file")
    sys.exit(1)


class IntegrationTester:
    """Run comprehensive integration tests"""

    def __init__(self):
        self.test_results = []
        self.start_time = None

    def log_test(self, name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            'name': name,
            'passed': passed,
            'message': message
        })
        print(f"{status} - {name}")
        if message:
            print(f"       {message}")

    def print_summary(self):
        """Print test summary"""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['passed'])
        failed = total - passed

        print(f"\n{'='*80}")
        print(f"📊 INTEGRATION TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success rate: {passed/total*100:.1f}%")

        if failed > 0:
            print(f"\n❌ Failed tests:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"   - {result['name']}: {result['message']}")

        elapsed = (datetime.now() - self.start_time).total_seconds()
        print(f"\n⏱️  Total time: {elapsed:.2f}s")
        print(f"{'='*80}")

        return passed == total

    async def test_simple_chunker(self):
        """Test 1: Simple Quality Chunker"""
        print(f"\n{'='*80}")
        print("TEST 1: Simple Quality Chunker")
        print(f"{'='*80}")

        try:
            from simple_quality_chunker import SimpleQualityChunker

            chunker = SimpleQualityChunker(min_tokens=100, max_tokens=200)

            test_content = """# Introduction

This is the first paragraph with some content. It contains multiple sentences to test the chunking behavior.

This is the second paragraph. It also has several sentences to ensure we have enough content for testing the chunker.

## Section 2

This is another section with more content. The chunker should split this into multiple chunks based on token count and paragraph boundaries.

Final paragraph with additional information to test the overlap feature between chunks."""

            chunks = chunker.chunk(test_content, document_id="test_doc")

            # Verify chunks were created
            self.log_test(
                "Chunker creates chunks",
                len(chunks) > 0,
                f"Created {len(chunks)} chunks"
            )

            # Verify chunk structure
            if chunks:
                first_chunk = chunks[0]
                has_id = 'id' in first_chunk
                has_content = 'content' in first_chunk
                has_tokens = 'token_count' in first_chunk

                self.log_test(
                    "Chunks have required fields",
                    has_id and has_content and has_tokens,
                    f"Fields: id={has_id}, content={has_content}, tokens={has_tokens}"
                )

                # Verify token counts
                token_counts_valid = all(
                    chunk['token_count'] >= 20  # Reasonable minimum
                    for chunk in chunks
                )

                self.log_test(
                    "Chunks have valid token counts",
                    token_counts_valid,
                    f"Token range: {min(c['token_count'] for c in chunks)}-{max(c['token_count'] for c in chunks)}"
                )

        except Exception as e:
            self.log_test("Chunker test", False, str(e))
            import traceback
            traceback.print_exc()

    async def test_merge_decision(self):
        """Test 2: Multi-Signal Merge Decision"""
        print(f"\n{'='*80}")
        print("TEST 2: Multi-Signal Merge Decision")
        print(f"{'='*80}")

        try:
            from merge_or_create_decision import MergeOrCreateDecision

            decision_maker = MergeOrCreateDecision()

            # Test case 1: Similar topics (should merge)
            new_topic = {
                'title': 'Python Lists Tutorial',
                'summary': 'Learn about Python list operations',
                'keywords': ['python', 'lists', 'tutorial', 'arrays'],
                'category': 'tutorial'
            }

            existing_doc = {
                'id': 'python_lists_101',
                'title': 'Python List Operations',
                'summary': 'Guide to Python lists and arrays',
                'keywords': ['python', 'lists', 'arrays', 'operations'],
                'category': 'tutorial'
            }

            decision = decision_maker.decide(new_topic, [existing_doc], use_llm_verification=False)

            self.log_test(
                "Similar topics identified",
                decision['action'] in ['merge', 'verify'],
                f"Action: {decision['action']}, confidence: {decision['confidence']:.3f}"
            )

            # Test case 2: Different topics (should create)
            different_topic = {
                'title': 'JavaScript Promises',
                'summary': 'Understanding async programming with promises',
                'keywords': ['javascript', 'promises', 'async', 'programming'],
                'category': 'guide'
            }

            decision2 = decision_maker.decide(different_topic, [existing_doc], use_llm_verification=False)

            self.log_test(
                "Different topics identified",
                decision2['action'] == 'create',
                f"Action: {decision2['action']}, confidence: {decision2['confidence']:.3f}"
            )

            # Test case 3: High keyword overlap (should merge)
            overlap_topic = {
                'title': 'Advanced List Methods',
                'summary': 'Deep dive into Python list methods',
                'keywords': ['python', 'lists', 'methods', 'operations', 'tutorial'],
                'category': 'tutorial'
            }

            decision3 = decision_maker.decide(overlap_topic, [existing_doc], use_llm_verification=False)

            keyword_overlap = decision3['signals'].get('keyword_overlap', 0)

            self.log_test(
                "High keyword overlap detected",
                keyword_overlap > 0.5,
                f"Keyword overlap: {keyword_overlap:.3f}, action: {decision3['action']}"
            )

        except Exception as e:
            self.log_test("Merge decision test", False, str(e))
            import traceback
            traceback.print_exc()

    async def test_document_creation(self):
        """Test 3: Document Creation with Chunks"""
        print(f"\n{'='*80}")
        print("TEST 3: Document Creation with Chunks")
        print(f"{'='*80}")

        try:
            from document_creator import DocumentCreator

            creator = DocumentCreator()

            test_topic = {
                'title': 'Python List Comprehensions',
                'category': 'tutorial',
                'summary': 'Learn how to use list comprehensions for concise data transformation in Python',
                'keywords': ['python', 'list-comprehension', 'syntax', 'iteration', 'functional-programming'],
                'content': """List comprehensions provide a concise way to create lists in Python. They consist of brackets containing an expression followed by a for clause, then zero or more for or if clauses.

## Basic Syntax

The basic syntax is: [expression for item in iterable]

For example:
- [x**2 for x in range(10)] creates a list of squares
- [x for x in range(10) if x % 2 == 0] creates a list of even numbers

## Nested Comprehensions

You can nest comprehensions for multi-dimensional data:
- [[x*y for x in range(3)] for y in range(3)] creates a 3x3 multiplication table

## Performance

List comprehensions are generally faster than equivalent for loops because they are optimized at the bytecode level. They can reduce code by 2-3 lines in many cases.

## Best Practices

Use list comprehensions when:
1. Creating simple transformations
2. Filtering sequences
3. Readability is not sacrificed

Avoid when:
1. Logic becomes too complex
2. Multiple nested levels (>2)
3. Side effects are needed""",
                'source_url': 'https://example.com/python-lists'
            }

            # Create document
            result = creator.create_documents_batch([test_topic])

            # Verify document creation
            self.log_test(
                "Document created successfully",
                result['success_count'] == 1,
                f"Created {result['success_count']} documents"
            )

            if result['documents']:
                doc = result['documents'][0]

                # Verify document structure
                self.log_test(
                    "Document has required fields",
                    all(key in doc for key in ['id', 'title', 'content', 'chunks', 'embedding', 'keywords']),
                    f"Document ID: {doc['id']}"
                )

                # Verify chunks
                chunks = doc.get('chunks', [])
                self.log_test(
                    "Document has chunks with embeddings",
                    len(chunks) > 0 and all('embedding' in c for c in chunks),
                    f"Chunks: {len(chunks)}, all have embeddings: {all('embedding' in c for c in chunks)}"
                )

                # Verify keywords
                keywords = doc.get('keywords', [])
                self.log_test(
                    "Document has keywords",
                    len(keywords) >= 3,
                    f"Keywords: {keywords}"
                )

                return doc  # Return for database test

        except Exception as e:
            self.log_test("Document creation test", False, str(e))
            import traceback
            traceback.print_exc()
            return None

    async def test_database_operations(self, test_doc: Dict):
        """Test 4: Database Save and Retrieval"""
        print(f"\n{'='*80}")
        print("TEST 4: Database Save and Retrieval")
        print(f"{'='*80}")

        if not test_doc:
            self.log_test("Database test skipped", False, "No test document provided")
            return None

        try:
            from chunked_document_database import ChunkedDocumentDatabase

            db = ChunkedDocumentDatabase()

            # Test save
            print("💾 Saving document to database...")
            save_result = db.insert_documents_batch([test_doc])

            self.log_test(
                "Document saved to database",
                save_result.get('success_count', 0) == 1,
                f"Saved {save_result.get('success_count', 0)} documents"
            )

            # Test retrieval
            print("🔍 Retrieving document from database...")
            doc_id = test_doc['id']
            retrieved = db.get_document_by_id(doc_id)

            self.log_test(
                "Document retrieved from database",
                retrieved is not None,
                f"Retrieved document: {retrieved['title'] if retrieved else 'None'}"
            )

            # Verify chunks were saved
            if retrieved:
                chunks = retrieved.get('chunks', [])
                self.log_test(
                    "Chunks saved and retrieved",
                    len(chunks) > 0,
                    f"Retrieved {len(chunks)} chunks"
                )

            # Test vector search
            print("🔎 Testing vector search...")
            query_embedding = test_doc['embedding']  # Use document's own embedding

            search_results = db.search_by_embedding(
                query_embedding,
                top_k=1,
                similarity_threshold=0.5
            )

            self.log_test(
                "Vector search finds document",
                len(search_results) > 0,
                f"Found {len(search_results)} results"
            )

            return retrieved

        except Exception as e:
            self.log_test("Database operations test", False, str(e))
            import traceback
            traceback.print_exc()
            return None

    async def test_document_merge(self, existing_doc: Dict):
        """Test 5: Document Merge with Re-chunking"""
        print(f"\n{'='*80}")
        print("TEST 5: Document Merge with Re-chunking")
        print(f"{'='*80}")

        if not existing_doc:
            self.log_test("Merge test skipped", False, "No existing document provided")
            return

        try:
            from document_merger import DocumentMerger

            merger = DocumentMerger()

            # Create a topic to merge
            merge_topic = {
                'title': 'List Comprehension Performance Tips',
                'category': 'tutorial',
                'summary': 'Performance optimization tips for list comprehensions',
                'keywords': ['python', 'list-comprehension', 'performance', 'optimization'],
                'content': """## Performance Optimization

When using list comprehensions, consider these optimization tips:

1. **Avoid repeated function calls**: Move function calls outside the comprehension when possible
2. **Use generator expressions for large data**: Generator expressions use less memory
3. **Profile before optimizing**: Use timeit to measure actual performance

Example of optimization:
```python
# Slow
result = [expensive_func(x) for x in data]

# Fast
func = expensive_func  # Local reference
result = [func(x) for x in data]
```""",
                'source_url': 'https://example.com/python-list-performance'
            }

            # Get chunk count before merge
            chunks_before = len(existing_doc.get('chunks', []))

            # Merge
            print(f"🔀 Merging topic into document...")
            merge_result = merger.merge_documents_batch([{
                'topic': merge_topic,
                'existing_document': existing_doc
            }])

            self.log_test(
                "Merge completed successfully",
                merge_result['success_count'] == 1,
                f"Merged {merge_result['success_count']} documents"
            )

            if merge_result['merged_documents']:
                merged_doc = merge_result['merged_documents'][0]

                # Verify content was merged
                merged_content = merged_doc.get('content', '')
                self.log_test(
                    "Content was merged",
                    len(merged_content) > len(existing_doc.get('content', '')),
                    f"Content length increased: {len(existing_doc.get('content', ''))} → {len(merged_content)} chars"
                )

                # Verify re-chunking happened
                chunks_after = len(merged_doc.get('chunks', []))
                self.log_test(
                    "Document was re-chunked",
                    chunks_after > 0,
                    f"Chunks: {chunks_before} → {chunks_after}"
                )

                # Verify chunks have embeddings
                self.log_test(
                    "New chunks have embeddings",
                    all('embedding' in c for c in merged_doc.get('chunks', [])),
                    f"All {chunks_after} chunks have embeddings"
                )

                # Verify keywords were merged
                merged_keywords = merged_doc.get('keywords', [])
                original_keywords = set(existing_doc.get('keywords', []))
                new_keywords = set(merge_topic.get('keywords', []))
                expected_keywords = original_keywords | new_keywords

                self.log_test(
                    "Keywords were merged",
                    set(merged_keywords) >= expected_keywords,
                    f"Keywords: {len(merged_keywords)} (expected >= {len(expected_keywords)})"
                )

                return merged_doc

        except Exception as e:
            self.log_test("Document merge test", False, str(e))
            import traceback
            traceback.print_exc()
            return None

    async def test_parent_document_retrieval(self):
        """Test 6: Parent Document Retrieval"""
        print(f"\n{'='*80}")
        print("TEST 6: Parent Document Retrieval (Search chunks, return documents)")
        print(f"{'='*80}")

        try:
            from chunked_document_database import ChunkedDocumentDatabase

            db = ChunkedDocumentDatabase()

            # Create a search query embedding
            # We'll use a simple query related to our test document
            import google.generativeai as genai
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

            query = "How do list comprehensions work in Python?"
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=query,
                task_type="retrieval_query"
            )
            query_embedding = result['embedding']

            # Search using Parent Document Retrieval
            print(f"🔎 Searching for: '{query}'")
            search_results = db.search_parent_documents(
                query_embedding=query_embedding,
                top_k=3,
                similarity_threshold=0.3
            )

            self.log_test(
                "Parent Document Retrieval works",
                len(search_results) > 0,
                f"Found {len(search_results)} documents"
            )

            # Verify results are DOCUMENTS, not chunks
            if search_results:
                first_result = search_results[0]
                is_document = 'content' in first_result and 'chunks' in first_result

                self.log_test(
                    "Returns full documents (not chunks)",
                    is_document,
                    f"Result has content: {'content' in first_result}, has chunks: {'chunks' in first_result}"
                )

                # Verify matching worked
                print(f"\n   Top result:")
                print(f"   Title: {first_result.get('title', 'N/A')}")
                print(f"   Score: {first_result.get('score', 0):.3f}")
                print(f"   Chunks matched: {first_result.get('matching_chunks', 0)}")

        except Exception as e:
            self.log_test("Parent Document Retrieval test", False, str(e))
            import traceback
            traceback.print_exc()

    async def run_all_tests(self):
        """Run all integration tests"""
        self.start_time = datetime.now()

        print(f"\n{'='*80}")
        print("🧪 INTEGRATION TESTING - SIMPLIFIED RAG WORKFLOW")
        print(f"{'='*80}")
        print(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        # Test 1: Simple chunker
        await self.test_simple_chunker()

        # Test 2: Merge decision
        await self.test_merge_decision()

        # Test 3: Document creation
        test_doc = await self.test_document_creation()

        # Test 4: Database operations
        retrieved_doc = await self.test_database_operations(test_doc)

        # Test 5: Document merge with re-chunking
        merged_doc = await self.test_document_merge(retrieved_doc)

        # Test 6: Parent Document Retrieval
        await self.test_parent_document_retrieval()

        # Print summary
        success = self.print_summary()

        return success


async def main():
    """Main test runner"""
    tester = IntegrationTester()
    success = await tester.run_all_tests()

    if success:
        print("\n🎉 All integration tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please review the output above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
