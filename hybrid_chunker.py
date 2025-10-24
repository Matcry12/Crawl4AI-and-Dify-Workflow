#!/usr/bin/env python3
"""
Hybrid Semantic Chunker for Crawl4AI

Implements optimized parent-child chunking with 3-level hierarchy:
- Level 1: Document summaries (100-200 tokens)
- Level 2: Semantic sections (200-400 tokens)
- Level 3: Semantic propositions (50-150 tokens)

Designed to integrate seamlessly with workflow_manager.py
"""

import os
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Suppress gRPC warnings
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglenge'] = '2'

import google.generativeai as genai
from utils.rate_limiter import get_llm_rate_limiter, get_embedding_rate_limiter


class HybridChunker:
    """
    Semantic chunker that splits documents into hierarchical chunks
    """

    def __init__(self, api_key: str = None, model_name: str = None):
        """
        Initialize chunker with Gemini API

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model_name: Model to use (defaults to CHUNKING_MODEL env var)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model_name = model_name or os.getenv('CHUNKING_MODEL', 'gemini-2.5-flash-lite')

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

        # Rate limiters
        self.llm_limiter = get_llm_rate_limiter()
        self.embedding_limiter = get_embedding_rate_limiter()

        # Chunking parameters (optimized for LLM comprehension)
        self.section_min_tokens = 150
        self.section_max_tokens = 400
        self.section_target_tokens = 300
        self.section_overlap_tokens = 50

        self.proposition_min_tokens = 30
        self.proposition_max_tokens = 150
        self.proposition_target_tokens = 100

        print("✅ Hybrid chunker initialized")
        print(f"   Model: {self.model_name}")
        print(f"   Section size: {self.section_min_tokens}-{self.section_max_tokens} tokens")
        print(f"   Proposition size: {self.proposition_min_tokens}-{self.proposition_max_tokens} tokens")


    def chunk_document(
        self,
        content: str,
        document_id: str,
        title: str,
        mode: str = "paragraph"
    ) -> Dict:
        """
        Chunk document into hierarchical structure

        Args:
            content: Document content (markdown format)
            document_id: Unique document identifier
            title: Document title
            mode: "paragraph" (split by headers) or "full-doc" (single parent)

        Returns:
            {
                "summary": str,
                "summary_embedding": List[float],
                "sections": [
                    {
                        "section_id": str,
                        "section_index": int,
                        "header": str,
                        "content": str,
                        "token_count": int,
                        "embedding": List[float],
                        "keywords": List[str],
                        "topics": List[str],
                        "section_type": str,
                        "propositions": [
                            {
                                "proposition_id": str,
                                "proposition_index": int,
                                "content": str,
                                "token_count": int,
                                "embedding": List[float],
                                "proposition_type": str,
                                "entities": List[str],
                                "keywords": List[str]
                            }
                        ]
                    }
                ],
                "stats": {
                    "total_sections": int,
                    "total_propositions": int,
                    "total_tokens": int
                }
            }
        """
        print(f"\n🔪 Chunking document: {title}")
        print(f"   Mode: {mode}")
        print(f"   Content length: {len(content)} chars")

        # Generate document summary first
        summary = self._generate_summary(content, title)
        summary_embedding = self._create_embedding(summary)

        # Split into sections based on mode
        if mode == "paragraph":
            raw_sections = self._split_by_headers(content)
        else:  # full-doc mode
            raw_sections = [{"header": None, "content": content}]

        print(f"   Initial sections: {len(raw_sections)}")

        # Process sections
        chunked_sections = []
        total_propositions = 0
        total_tokens = 0
        section_counter = 0  # Global section counter for unique indices

        for idx, raw_section in enumerate(raw_sections):
            section_chunks = self._split_large_section(raw_section['content'])

            for chunk_idx, chunk_content in enumerate(section_chunks):
                # Generate section ID (always include chunk index for consistency)
                section_id = f"{document_id}_section_{idx+1}_{chunk_idx+1}"

                header_text = raw_section.get('header') or 'Content'
                print(f"\n  📄 Section {idx+1}.{chunk_idx+1}: {header_text[:50]}")

                # Extract propositions
                propositions = self._extract_propositions(
                    chunk_content,
                    section_id
                )

                # Generate section embedding
                section_embedding = self._create_embedding(chunk_content)

                # Extract metadata
                keywords = self._extract_keywords(chunk_content)
                topics = self._extract_topics(chunk_content)
                section_type = self._classify_section(chunk_content, raw_section.get('header'))

                token_count = self._count_tokens(chunk_content)
                total_tokens += token_count

                chunked_section = {
                    "section_id": section_id,
                    "section_index": section_counter,
                    "header": raw_section.get('header'),
                    "content": chunk_content,
                    "token_count": token_count,
                    "embedding": section_embedding,
                    "keywords": keywords,
                    "topics": topics,
                    "section_type": section_type,
                    "propositions": propositions
                }

                chunked_sections.append(chunked_section)
                total_propositions += len(propositions)
                section_counter += 1  # Increment for next section

                print(f"    ✓ Tokens: {token_count}")
                print(f"    ✓ Propositions: {len(propositions)}")
                print(f"    ✓ Type: {section_type}")

        print(f"\n  ✅ Chunking complete:")
        print(f"     Sections: {len(chunked_sections)}")
        print(f"     Propositions: {total_propositions}")
        print(f"     Total tokens: {total_tokens}")

        return {
            "summary": summary,
            "summary_embedding": summary_embedding,
            "sections": chunked_sections,
            "stats": {
                "total_sections": len(chunked_sections),
                "total_propositions": total_propositions,
                "total_tokens": total_tokens
            }
        }


    def _generate_summary(self, content: str, title: str) -> str:
        """Generate document summary (100-200 tokens)"""
        prompt = f"""Generate a concise summary of this document in 100-200 tokens.

Title: {title}

Content:
{content[:2000]}

The summary should:
- Capture main topics and key points
- Be self-contained (no pronouns like "this document")
- Be suitable for high-level document filtering
- Include important keywords

Summary:"""

        try:
            self.llm_limiter.wait_if_needed()
            response = self.model.generate_content(prompt)
            summary = response.text.strip()
            return summary
        except Exception as e:
            print(f"    ⚠️  Summary generation failed: {e}")
            # Fallback: use first 200 tokens
            return ' '.join(content.split()[:200])


    def _split_by_headers(self, content: str) -> List[Dict]:
        """
        Split content by markdown headers (##, ###)

        Returns:
            List of {"header": str, "content": str}
        """
        header_pattern = r'^(#{2,3})\s+(.+)$'
        sections = []
        current_section = {"header": None, "content": ""}

        for line in content.split('\n'):
            match = re.match(header_pattern, line)

            if match:
                # Save previous section if has content
                if current_section["content"].strip():
                    sections.append(current_section)

                # Start new section
                header_level = len(match.group(1))
                header_text = match.group(2).strip()
                current_section = {
                    "header": header_text,
                    "level": header_level,
                    "content": ""
                }
            else:
                current_section["content"] += line + "\n"

        # Add last section
        if current_section["content"].strip():
            sections.append(current_section)

        # If no headers found, return entire content as one section
        if not sections:
            sections = [{"header": None, "content": content}]

        return sections


    def _split_large_section(self, content: str) -> List[str]:
        """
        Split large section into manageable chunks (200-400 tokens)
        with overlap for context preservation
        """
        tokens = self._count_tokens(content)

        # If section is already good size, return as-is
        if tokens <= self.section_max_tokens:
            return [content]

        # Split by paragraphs
        paragraphs = [p for p in content.split('\n\n') if p.strip()]

        chunks = []
        current_chunk = ""
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self._count_tokens(para)

            # If adding this paragraph would exceed max, save current chunk
            if current_tokens + para_tokens > self.section_max_tokens and current_chunk:
                chunks.append(current_chunk.strip())

                # Start new chunk with overlap (last 50 tokens of previous)
                overlap = ' '.join(current_chunk.split()[-self.section_overlap_tokens:])
                current_chunk = overlap + "\n\n" + para
                current_tokens = self._count_tokens(current_chunk)
            else:
                current_chunk += "\n\n" + para if current_chunk else para
                current_tokens += para_tokens

        # Add last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks


    def _extract_propositions(
        self,
        section_content: str,
        section_id: str
    ) -> List[Dict]:
        """
        Extract semantic propositions using LLM

        A proposition is a complete, self-contained statement
        """
        # For shorter sections, skip LLM and use sentence splitting
        token_count = self._count_tokens(section_content)
        if token_count < 150:
            return self._fallback_sentence_split(section_content, section_id)

        prompt = f"""Extract 3-6 semantic propositions from this text.

Each proposition must be:
- A complete, self-contained statement (no dangling "it", "this", "that")
- 50-150 tokens long
- Contains subject + verb + object
- Can stand alone without context

Text:
{section_content}

Format: Return ONLY the propositions, one per line, numbered like:
1. First proposition here
2. Second proposition here
3. etc
"""

        try:
            self.llm_limiter.wait_if_needed()
            response = self.model.generate_content(prompt)
            prop_text = response.text.strip()

            propositions = []
            for line in prop_text.split('\n'):
                line = line.strip()
                # Match numbered lines
                match = re.match(r'^\d+\.\s+(.+)$', line)
                if match:
                    prop_content = match.group(1).strip()
                    prop_tokens = self._count_tokens(prop_content)

                    # Validate token count
                    if self.proposition_min_tokens <= prop_tokens <= self.proposition_max_tokens:
                        prop_idx = len(propositions)
                        prop_id = f"{section_id}_prop_{prop_idx+1}"

                        prop_embedding = self._create_embedding(prop_content)

                        propositions.append({
                            "proposition_id": prop_id,
                            "proposition_index": prop_idx,
                            "content": prop_content,
                            "token_count": prop_tokens,
                            "embedding": prop_embedding,
                            "proposition_type": self._classify_proposition(prop_content),
                            "entities": self._extract_entities(prop_content),
                            "keywords": self._extract_keywords(prop_content)
                        })

            # If LLM didn't return enough, fallback to sentence split
            if len(propositions) < 2:
                return self._fallback_sentence_split(section_content, section_id)

            return propositions

        except Exception as e:
            print(f"    ⚠️  Proposition extraction failed: {e}")
            return self._fallback_sentence_split(section_content, section_id)


    def _fallback_sentence_split(
        self,
        content: str,
        section_id: str
    ) -> List[Dict]:
        """Fallback: split by sentences if LLM fails"""
        sentences = re.split(r'[.!?]+\s+', content)

        propositions = []
        for idx, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            token_count = self._count_tokens(sentence)
            if token_count < self.proposition_min_tokens:
                continue

            # Truncate if too long
            if token_count > self.proposition_max_tokens:
                words = sentence.split()
                sentence = ' '.join(words[:self.proposition_max_tokens])

            prop_id = f"{section_id}_prop_{idx+1}"

            propositions.append({
                "proposition_id": prop_id,
                "proposition_index": idx,
                "content": sentence,
                "token_count": self._count_tokens(sentence),
                "embedding": self._create_embedding(sentence),
                "proposition_type": "sentence",
                "entities": [],
                "keywords": []
            })

        return propositions


    def _classify_section(self, content: str, header: Optional[str]) -> str:
        """Classify section type"""
        text = (header or "") + " " + content
        text_lower = text.lower()

        if any(word in text_lower for word in ['introduction', 'overview', 'what is']):
            return 'introduction'
        elif any(word in text_lower for word in ['tutorial', 'how to', 'guide', 'step']):
            return 'tutorial'
        elif any(word in text_lower for word in ['example', 'sample', 'demo']):
            return 'example'
        elif any(word in text_lower for word in ['reference', 'api', 'specification']):
            return 'reference'
        else:
            return 'content'


    def _classify_proposition(self, text: str) -> str:
        """Classify proposition type"""
        text_lower = text.lower()

        if any(word in text_lower for word in ['is a', 'is an', 'refers to', 'means', 'defined as']):
            return 'definition'
        elif any(word in text_lower for word in ['first', 'then', 'next', 'finally', 'step']):
            return 'procedure'
        elif any(word in text_lower for word in ['for example', 'for instance', 'such as']):
            return 'example'
        elif any(word in text_lower for word in ['compared to', 'versus', 'while', 'whereas']):
            return 'comparison'
        else:
            return 'statement'


    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords (simple frequency-based)"""
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'has', 'have', 'had', 'will', 'would', 'can', 'could', 'should',
            'this', 'that', 'these', 'those', 'it', 'its'
        }

        words = re.findall(r'\b[a-z]+\b', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 3]

        # Get top 10 by frequency
        from collections import Counter
        keyword_counts = Counter(keywords)
        return [k for k, v in keyword_counts.most_common(10)]


    def _extract_topics(self, text: str) -> List[str]:
        """Extract topic tags"""
        topics = []

        topic_keywords = {
            'blockchain': ['blockchain', 'consensus', 'distributed', 'ledger'],
            'smart_contract': ['contract', 'solidity', 'eosio', 'deployment', 'deploy'],
            'development': ['develop', 'code', 'build', 'compile', 'programming'],
            'tutorial': ['tutorial', 'guide', 'how to', 'step by step'],
            'api': ['api', 'endpoint', 'request', 'response', 'rest'],
            'database': ['database', 'sql', 'query', 'table', 'schema'],
            'security': ['security', 'authentication', 'authorization', 'encryption'],
        }

        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                topics.append(topic)

        return topics


    def _extract_entities(self, text: str) -> List[str]:
        """Extract named entities (simplified)"""
        entities = []

        # Capitalized phrases (proper nouns)
        cap_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entities.extend(cap_phrases[:5])

        # Technical terms (camelCase, PascalCase)
        tech_terms = re.findall(r'\b[a-z]+[A-Z][a-zA-Z]+\b', text)
        entities.extend(tech_terms[:3])

        return list(set(entities))


    def _create_embedding(self, text: str) -> List[float]:
        """Generate 768-dim embedding using Gemini"""
        try:
            self.embedding_limiter.wait_if_needed()
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"    ⚠️  Embedding failed: {e}")
            return None


    def _count_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)"""
        # Rough estimate: 1 token ≈ 4 characters for English
        return max(1, len(text) // 4)


# ============================================================================
# Convenience function for workflow integration
# ============================================================================

def chunk_document(
    content: str,
    document_id: str,
    title: str,
    mode: str = "paragraph",
    api_key: str = None
) -> Dict:
    """
    Chunk document using hybrid semantic chunking

    Args:
        content: Document content (markdown)
        document_id: Unique document ID
        title: Document title
        mode: "paragraph" or "full-doc"
        api_key: Gemini API key

    Returns:
        Chunking results with summary, sections, and propositions
    """
    chunker = HybridChunker(api_key=api_key)
    return chunker.chunk_document(content, document_id, title, mode)
