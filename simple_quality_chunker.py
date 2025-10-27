#!/usr/bin/env python3
"""
Simple Quality Chunker for Crawl4AI

Basic text chunking with token limits and overlap.
No LLM calls - just clean, predictable chunking.
"""

import re
from typing import List, Dict
from datetime import datetime


class SimpleQualityChunker:
    """
    Simple quality-based text chunker.
    Splits text into chunks based on token limits with overlap.
    """

    def __init__(self, min_tokens: int = 200, max_tokens: int = 400, overlap_tokens: int = 50):
        """
        Initialize simple quality chunker.

        Args:
            min_tokens: Minimum tokens per chunk
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Overlap between chunks
        """
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count (simple heuristic: ~4 chars per token).

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Simple estimation: 1 token ≈ 4 characters
        return len(text) // 4

    def chunk(self, content: str, document_id: str = None) -> List[Dict]:
        """
        Chunk content into pieces with token limits and overlap.

        Args:
            content: Text content to chunk
            document_id: Optional document identifier

        Returns:
            List of chunk dicts with id, content, chunk_index, token_count
        """
        if not content or not content.strip():
            return []

        # Split into sentences (basic approach)
        sentences = self._split_into_sentences(content)

        if not sentences:
            return []

        chunks = []
        current_chunk_sentences = []
        current_token_count = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_tokens = self.estimate_tokens(sentence)

            # Check if adding this sentence would exceed max_tokens
            if current_token_count + sentence_tokens > self.max_tokens and current_chunk_sentences:
                # Finalize current chunk
                chunk_content = ' '.join(current_chunk_sentences)
                chunks.append({
                    'id': f"{document_id}_chunk_{chunk_index}" if document_id else f"chunk_{chunk_index}",
                    'content': chunk_content,
                    'chunk_index': chunk_index,
                    'token_count': current_token_count
                })

                # Start new chunk with overlap
                chunk_index += 1
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk_sentences,
                    self.overlap_tokens
                )
                current_chunk_sentences = overlap_sentences
                current_token_count = sum(self.estimate_tokens(s) for s in overlap_sentences)

            # Add sentence to current chunk
            current_chunk_sentences.append(sentence)
            current_token_count += sentence_tokens

        # Add final chunk if it meets minimum size
        if current_chunk_sentences:
            chunk_content = ' '.join(current_chunk_sentences)
            final_token_count = self.estimate_tokens(chunk_content)

            if final_token_count >= self.min_tokens or len(chunks) == 0:
                chunks.append({
                    'id': f"{document_id}_chunk_{chunk_index}" if document_id else f"chunk_{chunk_index}",
                    'content': chunk_content,
                    'chunk_index': chunk_index,
                    'token_count': final_token_count
                })
            elif chunks:
                # Too small - merge with last chunk
                last_chunk = chunks[-1]
                last_chunk['content'] += ' ' + chunk_content
                last_chunk['token_count'] = self.estimate_tokens(last_chunk['content'])

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be improved with better NLP)
        # Split on .!? followed by space and capital letter, or newlines
        text = text.strip()

        # Split by common sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])|(?<=\n)\s*(?=\S)', text)

        # Clean up and filter
        sentences = [s.strip() for s in sentences if s.strip()]

        # Handle very long sentences by splitting at other punctuation
        final_sentences = []
        for sentence in sentences:
            if self.estimate_tokens(sentence) > self.max_tokens:
                # Split long sentences at commas, semicolons
                parts = re.split(r'([,;])\s+', sentence)
                current_part = ""
                for i, part in enumerate(parts):
                    if i % 2 == 0:  # Actual text part
                        if self.estimate_tokens(current_part + part) > self.max_tokens // 2:
                            if current_part:
                                final_sentences.append(current_part.strip())
                            current_part = part
                        else:
                            current_part += part
                    else:  # Punctuation
                        current_part += part + " "
                if current_part:
                    final_sentences.append(current_part.strip())
            else:
                final_sentences.append(sentence)

        return final_sentences

    def _get_overlap_sentences(self, sentences: List[str], target_overlap_tokens: int) -> List[str]:
        """
        Get last N sentences that fit within overlap token budget.

        Args:
            sentences: List of sentences
            target_overlap_tokens: Target token count for overlap

        Returns:
            List of sentences for overlap
        """
        overlap_sentences = []
        overlap_tokens = 0

        # Work backwards from end
        for sentence in reversed(sentences):
            sentence_tokens = self.estimate_tokens(sentence)
            if overlap_tokens + sentence_tokens > target_overlap_tokens:
                break
            overlap_sentences.insert(0, sentence)
            overlap_tokens += sentence_tokens

        return overlap_sentences


if __name__ == "__main__":
    # Test the chunker
    chunker = SimpleQualityChunker(min_tokens=50, max_tokens=100, overlap_tokens=20)

    test_text = """
    This is the first sentence. This is the second sentence.
    This is the third sentence. This is the fourth sentence.
    This is the fifth sentence. This is the sixth sentence.
    This is the seventh sentence. This is the eighth sentence.
    """

    chunks = chunker.chunk(test_text, document_id="test_doc")

    print(f"Generated {len(chunks)} chunks:")
    for chunk in chunks:
        print(f"\nChunk {chunk['chunk_index']}:")
        print(f"  Tokens: {chunk['token_count']}")
        print(f"  Content: {chunk['content'][:100]}...")
