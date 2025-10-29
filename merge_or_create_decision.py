#!/usr/bin/env python3
"""
Merge or Create Decision Module

Determines whether a newly extracted topic should:
- Merge into an existing document (high similarity)
- Create a new document (low similarity or no match)
- Verify with LLM (uncertain cases)
"""

from typing import Dict, List, Optional
import google.generativeai as genai


class MergeOrCreateDecision:
    """
    Makes intelligent decisions about whether to merge topics into existing documents
    or create new ones, with optional LLM verification for uncertain cases.
    """

    def __init__(self, embedder, llm=None, merge_threshold: float = 0.85, create_threshold: float = 0.4):
        """
        Initialize decision maker.

        Args:
            embedder: EmbeddingSearcher instance for similarity calculation
            llm: Optional GenerativeModel for LLM verification
            merge_threshold: Similarity threshold for automatic merge (default: 0.85)
            create_threshold: Similarity threshold below which to create new doc (default: 0.4)
        """
        self.embedder = embedder
        self.llm = llm
        self.merge_threshold = merge_threshold
        self.create_threshold = create_threshold

    def decide(self, topic: Dict, existing_documents: List[Dict], use_llm_verification: bool = True) -> Dict:
        """
        Decide whether to merge topic into existing doc or create new one.

        Args:
            topic: Topic dict with 'title', 'content', etc.
            existing_documents: List of existing document dicts
            use_llm_verification: Whether to use LLM for uncertain cases

        Returns:
            Dict with 'action' (merge/create/verify), 'target_doc_id' (if merge),
            'similarity', 'reason', etc.
        """
        # If no existing documents, always create
        if not existing_documents:
            return {
                'action': 'create',
                'similarity': 0.0,
                'reason': 'No existing documents'
            }

        # Get topic embedding (use stored if available, otherwise create)
        if 'embedding' in topic and topic['embedding']:
            topic_embedding = topic['embedding']
        else:
            topic_text = f"{topic.get('title', '')}. {topic.get('summary', topic.get('content', ''))}"
            topic_embedding = self.embedder.create_embedding(topic_text)

        # Find best matching document
        best_match = None
        best_similarity = 0.0

        for doc in existing_documents:
            # Use STORED embedding if available (CRITICAL: don't regenerate!)
            if 'embedding' in doc and doc['embedding']:
                doc_embedding = doc['embedding']
            else:
                # Fallback: create embedding only if not stored
                # Use title + summary for consistency with how embeddings were created
                doc_text = f"{doc.get('title', '')}. {doc.get('summary', '')}"
                doc_embedding = self.embedder.create_embedding(doc_text)

            if not doc_embedding:
                continue  # Skip if embedding failed

            # Calculate similarity
            similarity = self.embedder.calculate_similarity(topic_embedding, doc_embedding)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = doc

        # Make decision based on similarity
        if best_similarity >= self.merge_threshold:
            # High confidence merge
            return {
                'action': 'merge',
                'target_doc_id': best_match['id'],
                'target_doc_title': best_match.get('title', 'Unknown'),
                'similarity': best_similarity,
                'reason': f'High similarity ({best_similarity:.3f}) with existing document',
                'confidence': 'high'
            }

        elif best_similarity <= self.create_threshold:
            # Low similarity - create new document
            return {
                'action': 'create',
                'similarity': best_similarity,
                'reason': f'Low similarity ({best_similarity:.3f}) - distinct topic',
                'confidence': 'high'
            }

        else:
            # Uncertain case - between thresholds
            if use_llm_verification and self.llm:
                # Use LLM to verify
                llm_decision = self._verify_with_llm(topic, best_match, best_similarity)
                return llm_decision
            else:
                # Default to create if no LLM available
                return {
                    'action': 'create',
                    'similarity': best_similarity,
                    'reason': f'Uncertain similarity ({best_similarity:.3f}) - creating new doc',
                    'confidence': 'low'
                }

    def _verify_with_llm(self, topic: Dict, candidate_doc: Dict, similarity: float) -> Dict:
        """
        Use LLM to verify whether topic should merge with candidate document.

        Args:
            topic: Topic to decide about
            candidate_doc: Best matching existing document
            similarity: Cosine similarity score

        Returns:
            Decision dict with LLM's recommendation
        """
        if not self.llm:
            return {
                'action': 'create',
                'similarity': similarity,
                'reason': 'LLM not available',
                'confidence': 'low'
            }

        # Create prompt for LLM
        # Use more content for better decision (1000 chars instead of 500)
        topic_content = topic.get('content', topic.get('summary', ''))
        topic_preview = topic_content[:1000] + ('...' if len(topic_content) > 1000 else '')

        doc_summary = candidate_doc.get('summary', '')
        doc_preview = doc_summary[:1000] + ('...' if len(doc_summary) > 1000 else '')

        prompt = f"""You are an expert AI system for document organization in a knowledge base. Your task is to decide whether a new topic should be MERGED into an existing document or if a NEW document should be CREATED.

## Context

The embedding similarity score is **{similarity:.3f}** (range: 0.0 = completely different, 1.0 = identical).
This is in the uncertain range (0.4-0.85), so we need your expert judgment.

## New Topic to Process

**Title:** {topic.get('title', 'N/A')}

**Content:**
{topic_preview}

## Candidate Existing Document

**Title:** {candidate_doc.get('title', 'N/A')}

**Summary:**
{doc_preview}

## Decision Guidelines

**MERGE** when:
- Both discuss the SAME core concept/subject (even if from different angles)
- The new topic would ADD value to the existing document (expand, clarify, provide examples)
- Users searching for one would likely want to see both together
- Example: "Python List Methods" + "Python List Comprehensions" → MERGE (both about Python lists)

**CREATE** when:
- They discuss DIFFERENT core concepts/subjects
- They belong to separate knowledge domains
- Merging would create confusion or dilute focus
- Example: "Python Lists" + "JavaScript Arrays" → CREATE (different languages)

## Few-Shot Examples

**Example 1: MERGE**
- New Topic: "Python Exception Handling - Try/Except Blocks"
- Existing Doc: "Python Error Handling Best Practices"
- Similarity: 0.72
- Decision: MERGE (same concept - error handling in Python)
- Reason: Both about Python error handling, would benefit from integration

**Example 2: CREATE**
- New Topic: "Node.js Package Management with npm"
- Existing Doc: "Python Package Management with pip"
- Similarity: 0.68
- Decision: CREATE (different ecosystems, different tools)
- Reason: Despite similar concepts, they're for different languages/ecosystems

**Example 3: MERGE**
- New Topic: "SQL JOIN Types - INNER vs OUTER"
- Existing Doc: "SQL Query Fundamentals and SELECT Statements"
- Similarity: 0.75
- Decision: MERGE (both SQL fundamentals)
- Reason: JOINs are part of SQL query fundamentals, natural fit

**Example 4: CREATE**
- New Topic: "CSS Flexbox Layout Techniques"
- Existing Doc: "HTML Semantic Elements and Structure"
- Similarity: 0.62
- Decision: CREATE (CSS vs HTML, different concerns)
- Reason: Different aspects of web development, separate focus areas

## Your Task

Analyze the new topic and existing document above. Consider:
1. Are they about the same core concept?
2. Would merging them help or confuse users?
3. Do they belong together in a knowledge base?

**Respond in this exact format:**

DECISION: [MERGE or CREATE]
CONFIDENCE: [HIGH, MEDIUM, or LOW]
REASONING: [One sentence explaining why]

Example responses:
- "DECISION: MERGE\\nCONFIDENCE: HIGH\\nREASONING: Both topics cover Python list operations and would benefit from integration."
- "DECISION: CREATE\\nCONFIDENCE: MEDIUM\\nREASONING: Different programming languages warrant separate documents despite similar concepts."
"""

        try:
            response = self.llm.generate_content(prompt)
            response_text = response.text.strip()

            # Parse structured response
            decision = None
            confidence = 'medium'  # default
            reasoning = None

            # Extract DECISION
            if 'DECISION:' in response_text:
                decision_line = [line for line in response_text.split('\n') if 'DECISION:' in line][0]
                if 'MERGE' in decision_line.upper():
                    decision = 'merge'
                elif 'CREATE' in decision_line.upper():
                    decision = 'create'

            # Extract CONFIDENCE
            if 'CONFIDENCE:' in response_text:
                confidence_line = [line for line in response_text.split('\n') if 'CONFIDENCE:' in line][0]
                if 'HIGH' in confidence_line.upper():
                    confidence = 'high'
                elif 'LOW' in confidence_line.upper():
                    confidence = 'low'
                else:
                    confidence = 'medium'

            # Extract REASONING
            if 'REASONING:' in response_text:
                reasoning_line = [line for line in response_text.split('\n') if 'REASONING:' in line][0]
                reasoning = reasoning_line.split('REASONING:', 1)[1].strip()

            # Fallback to simple parsing if structured format not found
            if not decision:
                response_upper = response_text.upper()
                if 'MERGE' in response_upper:
                    decision = 'merge'
                else:
                    decision = 'create'

            # Build response
            if decision == 'merge':
                return {
                    'action': 'merge',
                    'target_doc_id': candidate_doc['id'],
                    'target_doc_title': candidate_doc.get('title', 'Unknown'),
                    'similarity': similarity,
                    'reason': reasoning if reasoning else f'LLM verified merge (similarity: {similarity:.3f})',
                    'confidence': confidence,
                    'llm_used': True
                }
            else:
                return {
                    'action': 'create',
                    'similarity': similarity,
                    'reason': reasoning if reasoning else f'LLM recommended new document (similarity: {similarity:.3f})',
                    'confidence': confidence,
                    'llm_used': True
                }

        except Exception as e:
            print(f"⚠️  LLM verification failed: {e}")
            # Fall back to create on error
            return {
                'action': 'create',
                'similarity': similarity,
                'reason': f'LLM verification failed - creating new doc',
                'confidence': 'low',
                'llm_error': str(e)
            }


if __name__ == "__main__":
    # Example usage
    print("merge_or_create_decision.py - Restored")
    print("This module provides intelligent merge/create decisions for RAG documents")
