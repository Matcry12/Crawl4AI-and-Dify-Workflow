#!/usr/bin/env python3
"""
Embedding Search Module

Uses embeddings to find similar documents and determine merge/create/verify actions.
"""

import os

# Suppress gRPC warnings (must be set BEFORE importing genai)
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

from typing import List, Dict, Tuple, Optional
import google.generativeai as genai
from datetime import datetime


class EmbeddingSearcher:
    """
    Uses embeddings to search for similar documents and determine actions
    """

    def __init__(self, api_key: str = None):
        """
        Initialize embedding searcher

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Please set it in .env file")

        genai.configure(api_key=self.api_key)

        # Similarity thresholds
        self.MERGE_THRESHOLD = 0.85   # > 0.85: Obvious merge (skip LLM)
        self.CREATE_THRESHOLD = 0.4   # < 0.4: Obvious different (skip LLM)
        # 0.4-0.85: Uncertain, need LLM verification

        print("✅ Embedding searcher initialized")
        print(f"   Merge threshold: {self.MERGE_THRESHOLD}")
        print(f"   Create threshold: {self.CREATE_THRESHOLD}")

    def create_embedding(self, text: str) -> List[float]:
        """
        Create embedding for text using Gemini

        Args:
            text: Text to embed (typically topic summary)

        Returns:
            Embedding vector
        """
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"  ❌ Embedding error: {e}")
            return None

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0-1)
        """
        if not embedding1 or not embedding2:
            return 0.0

        # Cosine similarity
        import math

        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = math.sqrt(sum(a * a for a in embedding1))
        magnitude2 = math.sqrt(sum(b * b for b in embedding2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        similarity = dot_product / (magnitude1 * magnitude2)
        return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]

    def find_similar_documents(
        self,
        new_topic: Dict,
        existing_documents: List[Dict],
        mode_filter: str = None
    ) -> List[Tuple[Dict, float, str]]:
        """
        Find similar documents and determine action for each

        Args:
            new_topic: New topic to process
                {
                    "title": "...",
                    "summary": "...",
                    "description": "...",
                    "category": "..."
                }
            existing_documents: List of existing documents from database
                [
                    {
                        "id": "doc_1",
                        "title": "...",
                        "content": "...",
                        "embedding": [0.1, 0.2, ...],  # Pre-computed embedding
                        "category": "...",
                        "mode": "paragraph" or "full-doc"
                    }
                ]
            mode_filter: Optional mode to filter documents by ("paragraph" or "full-doc")
                        If specified, only compare with documents of this mode

        Returns:
            List of (document, similarity, action) tuples
            action: "merge", "create", or "verify"
        """
        if not existing_documents:
            return [(None, 0.0, "create")]

        # Filter documents by mode if specified
        if mode_filter:
            filtered_docs = [doc for doc in existing_documents if doc.get('mode') == mode_filter]
            if not filtered_docs:
                print(f"\n  ℹ️  No existing documents with mode '{mode_filter}' - will CREATE")
                return [(None, 0.0, "create")]
            existing_documents = filtered_docs
            print(f"\n  🔍 Searching for similar documents to: {new_topic['title']} (mode: {mode_filter})")
        else:
            print(f"\n  🔍 Searching for similar documents to: {new_topic['title']}")

        # Create embedding for new topic (use summary for embedding)
        new_embedding = self.create_embedding(new_topic['summary'])
        if not new_embedding:
            return [(None, 0.0, "create")]

        # Calculate similarity with each existing document
        results = []

        for doc in existing_documents:
            # Use pre-computed embedding if available, otherwise create new one
            if 'embedding' in doc and doc['embedding']:
                doc_embedding = doc['embedding']
            else:
                # Fallback: create embedding from summary or content
                text = doc.get('summary') or doc.get('content', '')
                if not text:
                    continue
                doc_embedding = self.create_embedding(text)
                if not doc_embedding:
                    continue

            # Calculate similarity
            similarity = self.calculate_similarity(new_embedding, doc_embedding)

            # Determine action based on similarity
            if similarity > self.MERGE_THRESHOLD:
                action = "merge"
                emoji = "🔗"
            elif similarity < self.CREATE_THRESHOLD:
                action = "create"
                emoji = "✨"
            else:
                action = "verify"
                emoji = "🤔"

            results.append((doc, similarity, action))

            print(f"    {emoji} {doc['title'][:50]}: {similarity:.3f} → {action.upper()}")

        # Sort by similarity (highest first)
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def process_topic(
        self,
        new_topic: Dict,
        existing_documents: List[Dict],
        mode_filter: str = None
    ) -> Dict:
        """
        Process a single topic and determine what to do

        Args:
            new_topic: New topic to process
            existing_documents: List of existing documents
            mode_filter: Optional mode to filter documents by ("paragraph" or "full-doc")

        Returns:
            Decision dictionary:
            {
                "action": "merge" | "create" | "verify",
                "target_document": {...} or None,
                "similarity": 0.0-1.0,
                "needs_llm": True/False,
                "reason": "explanation"
            }
        """
        print(f"\n{'='*80}")
        print(f"📋 Processing: {new_topic['title']}")
        print(f"   Category: {new_topic['category']}")
        if mode_filter:
            print(f"   Mode Filter: {mode_filter}")
        print(f"{'='*80}")

        # Find similar documents
        results = self.find_similar_documents(new_topic, existing_documents, mode_filter=mode_filter)

        if not results or results[0][1] == 0.0:
            # No existing documents or no similarity
            return {
                "action": "create",
                "target_document": None,
                "similarity": 0.0,
                "needs_llm": False,
                "reason": "No existing documents found"
            }

        # Get best match
        best_doc, best_similarity, action = results[0]

        # Build decision
        decision = {
            "action": action,
            "target_document": best_doc,
            "similarity": best_similarity,
            "needs_llm": action == "verify",
            "reason": self._get_reason(action, best_similarity)
        }

        # Print decision
        self._print_decision(decision)

        return decision

    def _get_reason(self, action: str, similarity: float) -> str:
        """Get explanation for decision"""
        if action == "merge":
            return f"Very high similarity ({similarity:.3f} > {self.MERGE_THRESHOLD}). Obvious merge."
        elif action == "create":
            return f"Very low similarity ({similarity:.3f} < {self.CREATE_THRESHOLD}). Obvious separate document."
        else:
            return f"Uncertain similarity ({similarity:.3f} between {self.CREATE_THRESHOLD}-{self.MERGE_THRESHOLD}). Needs LLM verification."

    def _print_decision(self, decision: Dict):
        """Print decision summary"""
        action_emoji = {
            "merge": "🔗",
            "create": "✨",
            "verify": "🤔"
        }

        print(f"\n{'─'*80}")
        print(f"{action_emoji[decision['action']]} DECISION: {decision['action'].upper()}")
        print(f"{'─'*80}")
        print(f"Similarity: {decision['similarity']:.3f}")
        print(f"Needs LLM: {'Yes' if decision['needs_llm'] else 'No'}")
        print(f"Reason: {decision['reason']}")

        if decision['target_document']:
            print(f"Target: {decision['target_document']['title']}")

        print(f"{'─'*80}")

    def batch_process_topics(
        self,
        new_topics: List[Dict],
        existing_documents: List[Dict],
        mode_filter: str = None
    ) -> Dict:
        """
        Process multiple topics and generate summary

        Args:
            new_topics: List of new topics
            existing_documents: List of existing documents
            mode_filter: Optional mode to filter documents by ("paragraph" or "full-doc")

        Returns:
            Summary dictionary with statistics
        """
        print(f"\n{'='*80}")
        print(f"🔄 BATCH PROCESSING: {len(new_topics)} topics")
        if mode_filter:
            print(f"   Mode Filter: {mode_filter}")
        print(f"{'='*80}")

        results = {
            "merge": [],
            "create": [],
            "verify": []
        }

        for i, topic in enumerate(new_topics, 1):
            print(f"\n[{i}/{len(new_topics)}]")
            decision = self.process_topic(topic, existing_documents, mode_filter=mode_filter)
            results[decision['action']].append({
                "topic": topic,
                "decision": decision
            })

        # Print summary
        self._print_batch_summary(results)

        return results

    def _print_batch_summary(self, results: Dict):
        """Print batch processing summary"""
        print(f"\n{'='*80}")
        print(f"📊 BATCH SUMMARY")
        print(f"{'='*80}")

        total = sum(len(results[action]) for action in results)

        print(f"\nTotal topics processed: {total}")
        print(f"\n🔗 MERGE (similarity > {self.MERGE_THRESHOLD}): {len(results['merge'])}")
        for item in results['merge']:
            topic = item['topic']
            decision = item['decision']
            print(f"   • {topic['title']} → {decision['target_document']['title']}")
            print(f"     Similarity: {decision['similarity']:.3f}")

        print(f"\n✨ CREATE (similarity < {self.CREATE_THRESHOLD}): {len(results['create'])}")
        for item in results['create']:
            topic = item['topic']
            print(f"   • {topic['title']}")

        print(f"\n🤔 VERIFY (needs LLM): {len(results['verify'])}")
        for item in results['verify']:
            topic = item['topic']
            decision = item['decision']
            print(f"   • {topic['title']} ↔ {decision['target_document']['title']}")
            print(f"     Similarity: {decision['similarity']:.3f}")

        print(f"\n{'='*80}")
        print(f"Skipped LLM calls: {len(results['merge']) + len(results['create'])} / {total}")
        print(f"Need LLM verification: {len(results['verify'])} / {total}")
        print(f"{'='*80}")


# Example usage and testing
async def main():
    """Test embedding search"""
    print("="*80)
    print("🔍 Embedding Search Test")
    print("="*80)

    # Initialize searcher
    try:
        searcher = EmbeddingSearcher()
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        return

    # Example new topics
    new_topics = [
        {
            "title": "Python Bug Reporting Process",
            "category": "guide",
            "summary": "Learn how to report bugs in Python using the GitHub issue tracker. Submit detailed reports with reproduction steps.",
            "description": "Full process for reporting Python bugs..."
        },
        {
            "title": "Installing Python Packages",
            "category": "tutorial",
            "summary": "How to install Python packages using pip. Learn about virtual environments and package management.",
            "description": "Complete guide to Python package installation..."
        },
        {
            "title": "Python String Formatting",
            "category": "tutorial",
            "summary": "Format strings in Python using f-strings, format() method, and old-style formatting. Examples included.",
            "description": "Comprehensive string formatting guide..."
        }
    ]

    # Example existing documents (mock)
    existing_documents = [
        {
            "id": "doc_1",
            "title": "How to Report Bugs in Python",
            "category": "guide",
            "summary": "Guide for reporting bugs found in Python. Use the issue tracker to submit bug reports with detailed information."
        },
        {
            "id": "doc_2",
            "title": "Python Package Management",
            "category": "tutorial",
            "summary": "Managing Python packages with pip. Installing, upgrading, and removing packages in your environment."
        },
        {
            "id": "doc_3",
            "title": "Working with Lists in Python",
            "category": "tutorial",
            "summary": "Python lists tutorial covering creation, indexing, slicing, and common list operations."
        }
    ]

    # Process topics
    results = searcher.batch_process_topics(new_topics, existing_documents)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
