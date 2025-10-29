#!/usr/bin/env python3
"""
Simplified Document Merger Module

Merges topics with existing documents and RE-CHUNKS after merge.

CRITICAL: After merging, old chunks no longer match the merged content.
We MUST delete old chunks and create new chunks from merged content.
"""

import os

# Suppress gRPC warnings
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

from typing import List, Dict, Optional
import google.generativeai as genai
from datetime import datetime
import json
from simple_quality_chunker import SimpleQualityChunker
from utils.rate_limiter import get_llm_rate_limiter, get_embedding_rate_limiter


class DocumentMerger:
    """
    Merges topics with existing documents and re-chunks the merged content
    """

    def __init__(self, api_key: str = None, model_name: str = None):
        """
        Initialize document merger

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model_name: Model to use (defaults to DOCUMENT_MERGER_MODEL env var)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model_name = model_name or os.getenv('DOCUMENT_MERGER_MODEL', 'gemini-2.5-flash-lite')

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Please set it in .env file")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

        # Rate limiters
        self.llm_limiter = get_llm_rate_limiter()
        self.embedding_limiter = get_embedding_rate_limiter()

        # Initialize simple quality chunker
        self.chunker = SimpleQualityChunker(
            min_tokens=200,
            max_tokens=400,
            overlap_tokens=50
        )

        print("✅ Simplified document merger initialized")
        print(f"   Model: {self.model_name}")
        print(f"   Chunker: SimpleQualityChunker (for re-chunking)")

    def create_embedding(self, text: str) -> list:
        """
        Create embedding for text using Gemini

        Args:
            text: Text to embed

        Returns:
            768-dimensional embedding vector
        """
        try:
            self.embedding_limiter.wait_if_needed()
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"  ⚠️  Embedding generation failed: {e}")
            return None

    def _parse_hybrid_response(
        self,
        response_text: str,
        fallback_content: str,
        existing_document: dict
    ) -> tuple[str, dict]:
        """
        Parse hybrid response format with delimiters and JSON

        Args:
            response_text: LLM response
            fallback_content: Content to use if parsing fails
            existing_document: Original document for fallback metadata

        Returns:
            (merged_content, metadata_dict)
        """
        import re

        # Extract reorganized content using delimiters
        # Try new format first (REORGANIZED), fallback to old format (MERGED)
        content_pattern_new = r'===REORGANIZED_CONTENT_START===(.*?)===REORGANIZED_CONTENT_END==='
        content_pattern_old = r'===MERGED_CONTENT_START===(.*?)===MERGED_CONTENT_END==='

        content_match = re.search(content_pattern_new, response_text, re.DOTALL)
        if not content_match:
            content_match = re.search(content_pattern_old, response_text, re.DOTALL)

        if content_match:
            merged_content = content_match.group(1).strip()
        else:
            # Fallback: try to find content without delimiters
            print(f"  ⚠️  Content delimiters not found, using fallback")
            merged_content = fallback_content

        # Extract metadata JSON
        json_pattern = r'===METADATA===(.*?)===METADATA_END==='
        json_match = re.search(json_pattern, response_text, re.DOTALL)

        metadata = {}
        if json_match:
            json_text = json_match.group(1).strip()

            # Clean markdown code blocks if present
            if json_text.startswith('```'):
                json_text = json_text.split('```')[1]
                if json_text.strip().startswith('json'):
                    json_text = json_text.strip()[4:]
            json_text = json_text.strip()

            try:
                metadata = json.loads(json_text)
            except json.JSONDecodeError as e:
                print(f"  ⚠️  Metadata JSON parsing failed: {e}")
                # Use fallback metadata
                metadata = {
                    "strategy": "unknown",
                    "summary": existing_document.get('summary', ''),
                    "changes_made": "Merge completed (metadata parse failed)"
                }
        else:
            # No metadata found, use fallbacks
            print(f"  ⚠️  Metadata section not found, using defaults")
            metadata = {
                "strategy": "unknown",
                "summary": existing_document.get('summary', ''),
                "changes_made": "Content merged"
            }

        # Validate merged content is not empty
        if not merged_content or len(merged_content.strip()) < 100:
            print(f"  ⚠️  Merged content too short, using fallback")
            merged_content = fallback_content

        return merged_content, metadata

    def merge_document(
        self,
        topic: Dict,
        existing_document: Dict
    ) -> Optional[Dict]:
        """
        Merge topic into existing document with RE-CHUNKING

        CRITICAL PROCESS:
        1. Merge content (LLM)
        2. Update document metadata
        3. DELETE old chunks (no longer valid!)
        4. CREATE new chunks from merged content
        5. Generate embeddings for new chunks
        6. Return updated document (database handles atomic save)

        Args:
            topic: New topic to merge
            existing_document: Existing document to merge into

        Returns:
            Merged document with NEW chunks
        """
        try:
            doc_title = existing_document.get('title', 'Unknown')
            topic_title = topic.get('title', 'Unknown')

            print(f"\n  🔀 Merging '{topic_title}' into '{doc_title}' (Append-Then-Rewrite)")

            # Step 1: APPEND manually (no LLM yet)
            existing_content = existing_document.get('content', '')
            new_content = topic.get('content', topic.get('description', ''))

            print(f"  📎 Step 1: Appending new content manually...")
            print(f"     Existing: {len(existing_content)} chars")
            print(f"     New: {len(new_content)} chars")

            # Manual append with clear separator
            appended_content = f"{existing_content}\n\n---\n\n{new_content}"

            print(f"     Appended: {len(appended_content)} chars")

            # Step 2: LLM reorganizes the appended content
            print(f"  🤖 Step 2: Using LLM to reorganize appended content...")

            prompt = f"""You are given a document with newly appended content. Your task is to REORGANIZE and REWRITE it into a cohesive, well-structured document.

DOCUMENT TITLE: {doc_title}

CURRENT CONTENT (with new content appended):
{appended_content}

YOUR TASK - REORGANIZE AND REWRITE:
The content above contains the original document + newly added information (separated by ---).

REORGANIZATION STRATEGY:
1. Read through ALL the content (both original and new sections)
2. Identify logical sections and themes
3. Group related information together
4. Remove the separator (---)
5. Reorganize into a logical, flowing structure
6. Rewrite transitions to make it coherent
7. Preserve 100% of the information - just reorganize it better

OUTPUT FORMAT (IMPORTANT - follow exactly):

===REORGANIZED_CONTENT_START===
[Write the complete reorganized content here]
[All information from both sections, but reorganized logically]
[Remove redundancy but keep all unique details]
[Can include ANY characters, quotes, code blocks, special chars]
[No JSON escaping needed]
===REORGANIZED_CONTENT_END===

===METADATA===
{{
  "strategy": "reorganize",
  "summary": "Brief summary of the reorganized document (max 200 characters)",
  "changes_made": "Brief description of how you reorganized the content"
}}
===METADATA_END===

CRITICAL RULES - REORGANIZATION:
✅ DO:
- PRESERVE 100% of important information from both sections
- Remove the --- separator and make it flow as ONE document
- Group related topics together logically
- Create smooth transitions between topics
- Eliminate true duplicates (exact same info stated twice)
- Keep ALL technical details, examples, code snippets
- Make it read as ONE cohesive document, not two glued together

❌ DON'T:
- Summarize or condense unique information
- Remove examples or details that add value
- Change technical accuracy
- Skip any important information from either section

GOAL: Transform the appended content into ONE well-organized, cohesive document that reads naturally.

OUTPUT FORMAT REMINDER:
1. First: ===REORGANIZED_CONTENT_START=== ... ===REORGANIZED_CONTENT_END===
2. Then: ===METADATA=== {{...}} ===METADATA_END===
"""

            print(f"  🤖 Using LLM to reorganize appended content...")
            self.llm_limiter.wait_if_needed()
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1
                )
            )
            response_text = response.text.strip()

            # Parse hybrid response
            try:
                merged_content, metadata = self._parse_hybrid_response(
                    response_text,
                    appended_content,  # Use appended_content as fallback, not existing
                    existing_document
                )

                merge_strategy = metadata.get('strategy', 'unknown')
                updated_summary = metadata.get('summary', existing_document.get('summary', ''))
                changes_made = metadata.get('changes_made', 'Content reorganized')

                print(f"  ✅ Reorganization strategy: {merge_strategy}")
                print(f"  📝 Changes: {changes_made}")

            except Exception as e:
                print(f"  ❌ Error parsing reorganization response: {e}")
                import traceback
                traceback.print_exc()

                # Fallback: keep the appended content (manual append without LLM reorganization)
                merged_content = appended_content
                updated_summary = existing_document.get('summary', '')
                merge_strategy = "append-only"
                changes_made = "Content appended without reorganization (LLM failed)"
                print(f"  ⚠️  Using fallback: keeping manually appended content")

            # Step 2: Update document metadata
            doc_id = existing_document.get('id')

            # Merge keywords (combine and deduplicate)
            existing_keywords = set(existing_document.get('keywords', []))
            new_keywords = set(topic.get('keywords', []))
            merged_keywords = list(existing_keywords | new_keywords)

            # Merge source URLs (create new list to avoid mutation)
            existing_urls = list(existing_document.get('source_urls', []))
            new_url = topic.get('source_url')
            if new_url and new_url not in existing_urls:
                existing_urls.append(new_url)

            # Step 3: Generate new document embedding (from updated summary)
            print(f"  🔢 Generating document embedding...")
            doc_embedding = self.create_embedding(updated_summary)

            if not doc_embedding:
                print(f"  ⚠️  Failed to generate document embedding")
                return None

            # Step 4: RE-CHUNK the merged content (CRITICAL!)
            print(f"  ✂️  RE-CHUNKING merged content...")
            print(f"     (Old chunks no longer match merged content)")

            new_chunks = self.chunker.chunk(merged_content, document_id=doc_id)

            if not new_chunks:
                print(f"  ⚠️  No chunks created from merged content")
                return None

            print(f"  ✅ Created {len(new_chunks)} new chunks")

            # Step 5: Generate embeddings for new chunks
            print(f"  🔢 Generating chunk embeddings...")
            chunks_with_embeddings = []

            for i, chunk in enumerate(new_chunks):
                chunk_embedding = self.create_embedding(chunk['content'])

                if chunk_embedding:
                    chunk['embedding'] = chunk_embedding
                    chunks_with_embeddings.append(chunk)
                else:
                    print(f"  ⚠️  Failed to generate embedding for chunk {i+1}")

            if not chunks_with_embeddings:
                print(f"  ⚠️  No chunks with embeddings")
                return None

            print(f"  ✅ Generated embeddings for {len(chunks_with_embeddings)}/{len(new_chunks)} chunks")

            # Step 6: Create updated document
            # Database will handle atomic transaction:
            # - Update document
            # - DELETE old chunks WHERE document_id = doc_id
            # - INSERT new chunks
            # - Record merge history

            updated_document = {
                'id': doc_id,
                'title': doc_title,
                'content': merged_content,
                'summary': updated_summary,
                'category': existing_document.get('category', 'general'),
                'keywords': merged_keywords,
                'source_urls': existing_urls,
                'embedding': doc_embedding,
                'chunks': chunks_with_embeddings,  # NEW chunks!
                'created_at': existing_document.get('created_at'),
                'updated_at': datetime.now().isoformat(),
                'merge_history': {
                    'source_topic_title': topic_title,
                    'merge_strategy': merge_strategy,
                    'changes_made': changes_made,
                    'merged_at': datetime.now().isoformat()
                }
            }

            print(f"  ✅ Document merged successfully:")
            print(f"     Content: {len(merged_content)} chars")
            print(f"     New chunks: {len(chunks_with_embeddings)} (old chunks will be deleted)")
            print(f"     Keywords: {len(merged_keywords)}")
            print(f"     Source URLs: {len(existing_urls)}")

            return updated_document

        except Exception as e:
            print(f"  ❌ Error merging document: {e}")
            import traceback
            traceback.print_exc()
            return None

    def merge_documents_batch(
        self,
        merge_pairs: List[Dict]
    ) -> Dict:
        """
        Merge multiple topics with their target documents

        Args:
            merge_pairs: List of dicts with:
                - topic: Topic to merge
                - existing_document: Document to merge into

        Returns:
            Results dictionary with:
            - merged_documents: List of merged documents
            - success_count: Number of successful merges
            - fail_count: Number of failed merges
            - failed_merges: List of failed merge titles
        """
        print(f"\n{'='*80}")
        print(f"🔀 BATCH DOCUMENT MERGE")
        print(f"{'='*80}")
        print(f"Merges to process: {len(merge_pairs)}")
        print(f"{'='*80}")

        merged_documents = []
        failed_merges = []

        for i, pair in enumerate(merge_pairs, 1):
            topic = pair.get('topic')
            existing_doc = pair.get('existing_document')

            if not topic or not existing_doc:
                print(f"\n[{i}/{len(merge_pairs)}] ⚠️  Invalid merge pair - skipping")
                failed_merges.append(f"Merge {i} (invalid pair)")
                continue

            print(f"\n[{i}/{len(merge_pairs)}]", end=" ")

            merged_doc = self.merge_document(topic, existing_doc)

            if merged_doc:
                merged_documents.append(merged_doc)
            else:
                failed_merges.append(f"{topic.get('title', 'Unknown')} → {existing_doc.get('title', 'Unknown')}")

        # Summary
        success_count = len(merged_documents)
        fail_count = len(failed_merges)

        print(f"\n{'='*80}")
        print(f"📊 BATCH MERGE SUMMARY")
        print(f"{'='*80}")
        print(f"✅ Success: {success_count}/{len(merge_pairs)} documents merged")

        if fail_count > 0:
            print(f"❌ Failed: {fail_count} merges")
            print(f"   Failed merges:")
            for title in failed_merges[:5]:
                print(f"   - {title}")
            if len(failed_merges) > 5:
                print(f"   ... and {len(failed_merges) - 5} more")

        # Calculate stats
        total_chunks = sum(len(doc.get('chunks', [])) for doc in merged_documents)
        avg_chunks = total_chunks / success_count if success_count > 0 else 0

        print(f"\n📈 Statistics:")
        print(f"   Total new chunks: {total_chunks}")
        print(f"   Average chunks per doc: {avg_chunks:.1f}")
        print(f"   ⚠️  Old chunks will be deleted on database save")

        print(f"{'='*80}")

        results = {
            'merged_documents': merged_documents,
            'success_count': success_count,
            'fail_count': fail_count,
            'failed_merges': failed_merges,
            'total_merged': success_count,
            'total_chunks': total_chunks
        }

        return results

    def save_merged_documents(
        self,
        results: Dict,
        output_dir: str = "merged_documents",
        save_to_db: bool = True
    ):
        """
        Save merged documents to files and database

        Database will handle atomic transaction for chunk replacement

        Args:
            results: Results from merge_documents_batch
            output_dir: Output directory for files
            save_to_db: Whether to save to database
        """
        from pathlib import Path
        import json

        merged_docs = results.get('merged_documents', [])

        if not merged_docs:
            print("⚠️  No merged documents to save")
            return

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save each document to file
        for doc in merged_docs:
            filename = f"{doc['id']}_merged_{datetime.now().strftime('%Y%m%d')}.json"
            filepath = output_path / filename

            # Save document (without embeddings - too large)
            doc_for_file = {
                'id': doc['id'],
                'title': doc['title'],
                'content': doc['content'],
                'summary': doc['summary'],
                'category': doc['category'],
                'keywords': doc['keywords'],
                'source_urls': doc['source_urls'],
                'updated_at': doc['updated_at'],
                'chunks_count': len(doc.get('chunks', [])),
                'merge_history': doc.get('merge_history', {})
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(doc_for_file, f, indent=2)

        print(f"\n💾 Saved {len(merged_docs)} merged documents to {output_dir}/")

        # Save to database if enabled
        if save_to_db:
            try:
                if os.getenv('USE_POSTGRESQL', 'true').lower() == 'true':
                    from chunked_document_database import ChunkedDocumentDatabase

                    db = ChunkedDocumentDatabase()

                    print(f"\n💾 Updating database with merged documents...")
                    print(f"   Each update will:")
                    print(f"   1. Update document content")
                    print(f"   2. DELETE old chunks")
                    print(f"   3. INSERT new chunks")
                    print(f"   4. Record merge history")
                    print(f"   (Atomic transactions ensure consistency)")

                    # Database has update_document_with_chunks() method that handles:
                    # BEGIN TRANSACTION
                    #   UPDATE documents SET ...
                    #   DELETE FROM chunks WHERE document_id = ...
                    #   INSERT INTO chunks ...
                    #   INSERT INTO merge_history ...
                    # COMMIT

                    saved_count = 0
                    for doc in merged_docs:
                        try:
                            success = db.update_document_with_chunks(doc)
                            if success:
                                saved_count += 1
                        except Exception as e:
                            print(f"  ⚠️  Failed to save {doc['id']}: {e}")

                    print(f"  ✅ Updated {saved_count}/{len(merged_docs)} documents in database")

                else:
                    print("⚠️  Database save skipped (PostgreSQL not enabled)")

            except Exception as e:
                print(f"⚠️  Database save failed: {e}")
                import traceback
                traceback.print_exc()


# Example usage
if __name__ == "__main__":
    merger = DocumentMerger()

    # Test merge
    test_topic = {
        'title': 'Python List Methods',
        'content': 'Additional list methods include sort(), reverse(), and clear().',
        'keywords': ['python', 'list', 'methods'],
        'source_url': 'https://example.com/python-list-methods'
    }

    existing_doc = {
        'id': 'python_lists_20250101',
        'title': 'Python Lists',
        'content': 'Lists in Python are mutable sequences. Common operations include append(), extend(), and remove().',
        'summary': 'Introduction to Python lists',
        'category': 'tutorial',
        'keywords': ['python', 'list'],
        'source_urls': ['https://example.com/python-lists'],
        'created_at': '2025-01-01T00:00:00'
    }

    result = merger.merge_documents_batch([{
        'topic': test_topic,
        'existing_document': existing_doc
    }])

    print(f"\n{'='*80}")
    print(f"Merge test complete: {result['success_count']} successful")
    print(f"{'='*80}")
