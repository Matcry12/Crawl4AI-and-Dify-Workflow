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

        # Get topic embedding
        topic_text = f"{topic.get('title', '')} {topic.get('content', '')}"
        topic_embedding = self.embedder.create_embedding(topic_text)

        # Find best matching document
        best_match = None
        best_similarity = 0.0

        for doc in existing_documents:
            # Get document embedding
            doc_text = f"{doc.get('title', '')} {doc.get('summary', '')} {doc.get('content', '')}"
            doc_embedding = self.embedder.create_embedding(doc_text)

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
        prompt = f"""You are a document similarity expert. Decide if a new topic should be MERGED into an existing document or if a NEW document should be CREATED.

**New Topic:**
Title: {topic.get('title', 'N/A')}
Content: {topic.get('content', '')[:500]}...

**Candidate Existing Document:**
Title: {candidate_doc.get('title', 'N/A')}
Summary: {candidate_doc.get('summary', '')[:500]}...

**Similarity Score:** {similarity:.3f} (0.0 = completely different, 1.0 = identical)

**Instructions:**
- If the topics are about the SAME subject/concept, respond with: MERGE
- If the topics are about DIFFERENT subjects/concepts, respond with: CREATE
- Consider: Are they discussing the same core idea, even if from different angles?

Respond with ONLY one word: MERGE or CREATE
"""

        try:
            response = self.llm.generate_content(prompt)
            llm_action = response.text.strip().upper()

            if 'MERGE' in llm_action:
                return {
                    'action': 'merge',
                    'target_doc_id': candidate_doc['id'],
                    'target_doc_title': candidate_doc.get('title', 'Unknown'),
                    'similarity': similarity,
                    'reason': f'LLM verified merge (similarity: {similarity:.3f})',
                    'confidence': 'medium',
                    'llm_used': True
                }
            else:
                return {
                    'action': 'create',
                    'similarity': similarity,
                    'reason': f'LLM recommended new document (similarity: {similarity:.3f})',
                    'confidence': 'medium',
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
