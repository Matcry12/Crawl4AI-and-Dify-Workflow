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

    def create_embeddings_batch(self, texts: list) -> list:
        """
        Create embeddings for multiple texts in batch (MUCH faster and cheaper!)

        This method uses batch API to generate embeddings for multiple texts
        in a single API call, reducing costs by 99% and improving speed by 40x.

        Args:
            texts: List of texts to embed

        Returns:
            List of 768-dimensional embedding vectors (same order as input)
            Returns None for any text that failed to embed
        """
        if not texts:
            return []

        # Check if batch embedding is enabled (default: True)
        batch_enabled = os.getenv('BATCH_EMBEDDING_ENABLED', 'True').lower() == 'true'

        if not batch_enabled:
            # Fall back to sequential if batch is disabled
            embeddings = []
            for text in texts:
                emb = self.create_embedding(text)
                embeddings.append(emb)
            return embeddings

        # Get batch size from environment (default: 100, Gemini's maximum)
        BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))
        BATCH_SIZE = min(BATCH_SIZE, 100)  # Ensure it doesn't exceed Gemini's limit
        all_embeddings = []

        try:
            # Process in batches of 100
            for i in range(0, len(texts), BATCH_SIZE):
                batch = texts[i:i + BATCH_SIZE]

                # Rate limit before each batch
                self.embedding_limiter.wait_if_needed()

                # Call batch embedding API
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=batch,
                    task_type="retrieval_document"
                )

                # DEBUG: Log what we received
                print(f"  🔍 DEBUG: Batch size={len(batch)}, Result type={type(result)}")
                if hasattr(result, 'embedding'):
                    print(f"  🔍 DEBUG: result.embedding exists, type={type(result.embedding)}")
                if hasattr(result, 'embeddings'):
                    print(f"  🔍 DEBUG: result.embeddings exists, count={len(result.embeddings)}")

                # Extract embeddings from result - Gemini returns different formats
                if hasattr(result, 'embedding'):
                    # Single embedding via attribute (batch of 1)
                    emb = result.embedding
                    if isinstance(emb, list) and len(emb) > 0 and isinstance(emb[0], list):
                        # Nested structure detected
                        # Check if it's double-nested: [[emb1, emb2, emb3, ...]] (all embeddings in one wrapper)
                        if len(emb) == 1 and isinstance(emb[0], list) and len(emb[0]) == len(batch):
                            # Double-nested case: [[emb1, emb2, ...]] where inner list has ALL embeddings
                            print(f"  🔍 DEBUG: Detected double-nested format, flattening...")
                            all_embeddings.extend(emb[0])  # Extract the inner list with all embeddings
                        else:
                            # Regular nested: [[emb1], [emb2], [emb3], ...] (each embedding wrapped separately)
                            all_embeddings.extend(emb)
                    else:
                        # Flat: [...]
                        all_embeddings.append(emb)
                elif hasattr(result, 'embeddings'):
                    # Multiple embeddings via attribute
                    for emb in result.embeddings:
                        if hasattr(emb, 'values'):
                            all_embeddings.append(emb.values)
                        elif isinstance(emb, list):
                            all_embeddings.append(emb)
                        else:
                            all_embeddings.append(list(emb))
                elif isinstance(result, dict) and 'embedding' in result:
                    # Dict with 'embedding' key
                    emb = result['embedding']
                    print(f"  🔍 DEBUG: Dict with 'embedding', type={type(emb)}, len={len(emb) if isinstance(emb, list) else 'N/A'}")

                    # Check if it contains multiple embeddings or single embedding
                    if isinstance(emb, list) and len(emb) > 0:
                        # Could be: [emb1, emb2, ...] or [[emb1], [emb2], ...]
                        if isinstance(emb[0], list):
                            # Multiple embeddings, each wrapped: [[emb1], [emb2], ...]
                            # Apply the same double-nested check
                            if len(emb) == 1 and len(emb[0]) == len(batch):
                                print(f"  🔍 DEBUG: Dict double-nested format detected")
                                all_embeddings.extend(emb[0])
                            else:
                                all_embeddings.extend(emb)
                        elif len(emb) == len(batch):
                            # Multiple flat embeddings: [emb1, emb2, ...]
                            # But emb1, emb2 are NOT lists (just single values)
                            # This is ambiguous - could be one embedding with batch_size dimensions
                            # OR batch_size embeddings with 1 dimension each
                            # Check if first element looks like an embedding (has multiple values)
                            if hasattr(emb[0], '__len__') and len(emb[0]) > 1:
                                # Looks like multiple embeddings
                                all_embeddings.extend(emb)
                            else:
                                # Single embedding vector
                                all_embeddings.append(emb)
                        else:
                            # Single embedding vector
                            all_embeddings.append(emb)
                    else:
                        # Single embedding
                        all_embeddings.append(emb)
                elif isinstance(result, dict) and 'embeddings' in result:
                    # Dict with multiple embeddings
                    for emb_data in result['embeddings']:
                        if isinstance(emb_data, dict) and 'values' in emb_data:
                            all_embeddings.append(emb_data['values'])
                        elif isinstance(emb_data, list):
                            all_embeddings.append(emb_data)
                        else:
                            all_embeddings.append(list(emb_data))
                elif isinstance(result, list):
                    # Direct list of embeddings [[...], [...]]
                    all_embeddings.extend(result)
                else:
                    # Unknown format - try to convert
                    print(f"  ⚠️  Unknown embedding result format: {type(result)}")
                    all_embeddings.extend(list(result))

            return all_embeddings

        except Exception as e:
            print(f"  ⚠️  Batch embedding generation failed: {e}")
            print(f"     Falling back to sequential embedding...")

            # Fallback to sequential if batch fails
            embeddings = []
            for text in texts:
                emb = self.create_embedding(text)
                embeddings.append(emb)
            return embeddings

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

            # Step 5: Generate embeddings for chunks using BATCH API (99% cost reduction!)
            print(f"  🔢 Generating chunk embeddings (batch mode)...")
            chunk_texts = [chunk['content'] for chunk in new_chunks]

            # Call batch API - generates ALL embeddings in 1-2 API calls instead of N calls
            chunk_embeddings = self.create_embeddings_batch(chunk_texts)

            # Attach embeddings to chunks
            chunks_with_embeddings = []
            for i, (chunk, embedding) in enumerate(zip(new_chunks, chunk_embeddings)):
                if embedding:
                    # CRITICAL FIX: Flatten nested array if needed (Gemini API format issue)
                    # PostgreSQL pgvector requires flat [float, ...] not nested [[float, ...]]
                    if isinstance(embedding, list) and len(embedding) > 0:
                        if isinstance(embedding[0], list):
                            # Nested array [[...]] detected - flatten to [...]
                            embedding = embedding[0]
                            print(f"  ⚠️  Flattened nested embedding array for chunk {i+1}")

                    chunk['embedding'] = embedding
                    chunks_with_embeddings.append(chunk)
                else:
                    print(f"  ⚠️  Failed to generate embedding for chunk {i+1}")

            if not chunks_with_embeddings:
                print(f"  ⚠️  No chunks with embeddings")
                return None

            print(f"  ✅ Generated embeddings for {len(chunks_with_embeddings)}/{len(new_chunks)} chunks (batch mode)")

            # Show cost metrics if enabled
            show_metrics = os.getenv('SHOW_COST_METRICS', 'True').lower() == 'true'
            if show_metrics and len(new_chunks) > 0:
                batch_size = int(os.getenv('BATCH_SIZE', '100'))
                api_calls_made = (len(new_chunks) + batch_size - 1) // batch_size
                api_calls_saved = len(new_chunks) - api_calls_made
                reduction_pct = (api_calls_saved / len(new_chunks) * 100) if len(new_chunks) > 0 else 0
                print(f"     💰 API calls saved: {api_calls_saved} calls ({reduction_pct:.0f}% reduction)")

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

    def merge_multiple_topics_into_document(
        self,
        topics: List[Dict],
        existing_document: Dict
    ) -> Optional[Dict]:
        """
        Merge MULTIPLE topics into existing document in ONE operation (5x cost reduction!)

        CRITICAL OPTIMIZATION:
        Instead of calling merge_document() N times (5 LLM calls, 5 chunk ops, 5 embed ops),
        this method merges ALL topics at once:
        - Appends ALL topics → 1 LLM call → 1 chunk operation → 1 embedding batch

        Example cost comparison for 5 topics → same document:
        - OLD (sequential): 5 LLM calls + 124 embeddings = $0.35
        - NEW (batch): 1 LLM call + 30 embeddings = $0.08
        - SAVINGS: 77% cost reduction (5x → 1x multiplier)

        Args:
            topics: List of topics to merge
            existing_document: Existing document to merge into

        Returns:
            Merged document with NEW chunks
        """
        try:
            doc_title = existing_document.get('title', 'Unknown')
            num_topics = len(topics)

            print(f"\n  🔀 BATCH MERGE: {num_topics} topics into '{doc_title}' (5x cost reduction!)")

            # Step 1: APPEND ALL topics manually (no LLM yet)
            existing_content = existing_document.get('content', '')

            print(f"  📎 Step 1: Appending {num_topics} topics manually...")
            print(f"     Existing: {len(existing_content)} chars")

            # Build appended content with all topics
            appended_content = existing_content
            topic_titles = []

            for i, topic in enumerate(topics, 1):
                topic_title = topic.get('title', f'Topic {i}')
                topic_titles.append(topic_title)
                new_content = topic.get('content', topic.get('description', ''))

                print(f"     [{i}/{num_topics}] Appending '{topic_title}' ({len(new_content)} chars)")

                # Append with clear separator
                appended_content = f"{appended_content}\n\n---\n\n{new_content}"

            print(f"     Total appended: {len(appended_content)} chars")

            # Step 2: LLM reorganizes ALL appended content in ONE call
            print(f"  🤖 Step 2: Using LLM to reorganize ALL {num_topics} topics at once...")

            topics_list_str = ', '.join([f"'{t}'" for t in topic_titles])

            prompt = f"""You are given a document with {num_topics} newly appended topics. Your task is to REORGANIZE and REWRITE it into a cohesive, well-structured document.

DOCUMENT TITLE: {doc_title}

TOPICS BEING MERGED: {topics_list_str}

CURRENT CONTENT (with {num_topics} new topics appended):
{appended_content}

YOUR TASK - REORGANIZE AND REWRITE:
The content above contains the original document + {num_topics} newly added topics (separated by ---).

REORGANIZATION STRATEGY:
1. Read through ALL the content (original + all {num_topics} new topics)
2. Identify logical sections and themes across ALL content
3. Group related information together
4. Remove ALL separators (---)
5. Reorganize into a logical, flowing structure
6. Rewrite transitions to make it coherent
7. Preserve 100% of the information - just reorganize it better
8. Create ONE cohesive document, not {num_topics+1} separate sections glued together

OUTPUT FORMAT (IMPORTANT - follow exactly):

===REORGANIZED_CONTENT_START===
[Write the complete reorganized content here]
[All information from ALL sections, but reorganized logically]
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
- PRESERVE 100% of important information from ALL sections
- Remove ALL --- separators and make it flow as ONE document
- Group related topics together logically
- Create smooth transitions between topics
- Eliminate true duplicates (exact same info stated multiple times)
- Keep ALL technical details, examples, code snippets
- Make it read as ONE cohesive document

❌ DON'T:
- Summarize or condense unique information
- Remove examples or details that add value
- Change technical accuracy
- Skip any important information from ANY section

GOAL: Transform the appended content with {num_topics} topics into ONE well-organized, cohesive document that reads naturally.

OUTPUT FORMAT REMINDER:
1. First: ===REORGANIZED_CONTENT_START=== ... ===REORGANIZED_CONTENT_END===
2. Then: ===METADATA=== {{...}} ===METADATA_END===
"""

            print(f"  🤖 Calling LLM once for ALL {num_topics} topics...")
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
                    appended_content,
                    existing_document
                )

                merge_strategy = metadata.get('strategy', 'unknown')
                updated_summary = metadata.get('summary', existing_document.get('summary', ''))
                changes_made = metadata.get('changes_made', f'Reorganized {num_topics} topics')

                print(f"  ✅ Reorganization strategy: {merge_strategy}")
                print(f"  📝 Changes: {changes_made}")

            except Exception as e:
                print(f"  ❌ Error parsing reorganization response: {e}")
                import traceback
                traceback.print_exc()

                # Fallback: keep the appended content
                merged_content = appended_content
                updated_summary = existing_document.get('summary', '')
                merge_strategy = "append-only"
                changes_made = f"Content appended without reorganization (LLM failed)"
                print(f"  ⚠️  Using fallback: keeping manually appended content")

            # Step 3: Update document metadata
            doc_id = existing_document.get('id')

            # Merge keywords from ALL topics
            all_keywords = set(existing_document.get('keywords', []))
            for topic in topics:
                topic_keywords = set(topic.get('keywords', []))
                all_keywords |= topic_keywords
            merged_keywords = list(all_keywords)

            # Merge source URLs from ALL topics
            existing_urls = list(existing_document.get('source_urls', []))
            for topic in topics:
                new_url = topic.get('source_url')
                if new_url and new_url not in existing_urls:
                    existing_urls.append(new_url)

            # Step 4: Generate new document embedding
            print(f"  🔢 Generating document embedding...")
            doc_embedding = self.create_embedding(updated_summary)

            if not doc_embedding:
                print(f"  ⚠️  Failed to generate document embedding")
                return None

            # Step 5: RE-CHUNK the merged content ONCE (not N times!)
            print(f"  ✂️  RE-CHUNKING merged content ONCE...")
            print(f"     (Old chunks no longer match merged content)")

            new_chunks = self.chunker.chunk(merged_content, document_id=doc_id)

            if not new_chunks:
                print(f"  ⚠️  No chunks created from merged content")
                return None

            print(f"  ✅ Created {len(new_chunks)} new chunks")

            # Step 6: Generate embeddings for chunks ONCE using BATCH API
            print(f"  🔢 Generating chunk embeddings ONCE (batch mode)...")
            chunk_texts = [chunk['content'] for chunk in new_chunks]

            # Call batch API - generates ALL embeddings in 1-2 API calls
            chunk_embeddings = self.create_embeddings_batch(chunk_texts)

            # Attach embeddings to chunks
            chunks_with_embeddings = []
            for i, (chunk, embedding) in enumerate(zip(new_chunks, chunk_embeddings)):
                if embedding:
                    # CRITICAL FIX: Flatten nested array if needed
                    if isinstance(embedding, list) and len(embedding) > 0:
                        if isinstance(embedding[0], list):
                            embedding = embedding[0]
                            print(f"  ⚠️  Flattened nested embedding array for chunk {i+1}")

                    chunk['embedding'] = embedding
                    chunks_with_embeddings.append(chunk)
                else:
                    print(f"  ⚠️  Failed to generate embedding for chunk {i+1}")

            if not chunks_with_embeddings:
                print(f"  ⚠️  No chunks with embeddings")
                return None

            print(f"  ✅ Generated embeddings for {len(chunks_with_embeddings)}/{len(new_chunks)} chunks (batch mode)")

            # Show cost metrics
            show_metrics = os.getenv('SHOW_COST_METRICS', 'True').lower() == 'true'
            if show_metrics:
                batch_size = int(os.getenv('BATCH_SIZE', '100'))
                api_calls_made = (len(new_chunks) + batch_size - 1) // batch_size
                api_calls_saved = len(new_chunks) - api_calls_made
                reduction_pct = (api_calls_saved / len(new_chunks) * 100) if len(new_chunks) > 0 else 0
                print(f"     💰 Embedding API calls: {api_calls_made} (saved {api_calls_saved} calls, {reduction_pct:.0f}% reduction)")
                print(f"     💰 LLM calls: 1 (instead of {num_topics} sequential calls, {(1 - 1/num_topics)*100:.0f}% reduction)")

            # Step 7: Create updated document
            updated_document = {
                'id': doc_id,
                'title': doc_title,
                'content': merged_content,
                'summary': updated_summary,
                'category': existing_document.get('category', 'general'),
                'keywords': merged_keywords,
                'source_urls': existing_urls,
                'embedding': doc_embedding,
                'chunks': chunks_with_embeddings,
                'created_at': existing_document.get('created_at'),
                'updated_at': datetime.now().isoformat(),
                'merge_history': {
                    'source_topic_titles': topic_titles,
                    'num_topics_merged': num_topics,
                    'merge_strategy': merge_strategy,
                    'changes_made': changes_made,
                    'merged_at': datetime.now().isoformat()
                }
            }

            print(f"  ✅ BATCH MERGE completed successfully:")
            print(f"     Topics merged: {num_topics} (in ONE operation!)")
            print(f"     Content: {len(merged_content)} chars")
            print(f"     New chunks: {len(chunks_with_embeddings)} (old chunks will be deleted)")
            print(f"     Keywords: {len(merged_keywords)}")
            print(f"     Source URLs: {len(existing_urls)}")

            return updated_document

        except Exception as e:
            print(f"  ❌ Error in batch merge: {e}")
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
