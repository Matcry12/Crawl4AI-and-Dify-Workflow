#!/usr/bin/env python3
"""
LLM Verifier Module

Uses LLM to verify whether two topics are similar enough to merge
or different enough to create separate documents.

This is used for topics with uncertain similarity (0.4-0.85) where
embedding similarity alone is not enough to make a confident decision.
"""

import os

# Suppress gRPC warnings
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

from typing import Dict, List
import google.generativeai as genai


class LLMVerifier:
    """
    Uses LLM to verify topic similarity when embedding similarity is uncertain.

    For topics with similarity scores between 0.4-0.85, we need LLM judgment
    to decide if they should be merged or created as separate documents.
    """

    def __init__(self, model_name: str = None):
        """
        Initialize LLM verifier

        Args:
            model_name: Gemini model to use (defaults to LLM_VERIFIER_MODEL env var)
        """
        # Configure Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")

        self.model_name = model_name or os.getenv('LLM_VERIFIER_MODEL', 'gemini-2.5-flash-lite')

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.model_name)

        print(f"✅ LLM verifier initialized")
        print(f"   Model: {self.model_name}")

    def verify_topic_similarity(
        self,
        new_topic: Dict,
        existing_document: Dict,
        similarity_score: float
    ) -> Dict:
        """
        Use LLM to verify if a new topic should be merged with an existing document
        or created as a separate document.

        Args:
            new_topic: New topic to verify
            existing_document: Existing document with uncertain similarity
            similarity_score: Embedding similarity score (0.4-0.85)

        Returns:
            Decision dictionary:
            {
                "action": "merge" | "create",
                "confidence": 0.0-1.0,
                "reasoning": "explanation from LLM",
                "original_similarity": 0.4-0.85
            }
        """
        # Create prompt for LLM
        prompt = self._create_verification_prompt(new_topic, existing_document, similarity_score)

        # Call LLM
        try:
            response = self.model.generate_content(prompt)
            decision = self._parse_llm_response(response.text, similarity_score)
            return decision

        except Exception as e:
            print(f"   ⚠️  LLM verification failed: {e}")
            # Fallback: if similarity >= 0.65, merge; otherwise create
            fallback_action = "merge" if similarity_score >= 0.65 else "create"
            return {
                "action": fallback_action,
                "confidence": 0.5,
                "reasoning": f"LLM call failed, using fallback rule (threshold: 0.65)",
                "original_similarity": similarity_score,
                "llm_error": str(e)
            }

    def _create_verification_prompt(
        self,
        new_topic: Dict,
        existing_document: Dict,
        similarity_score: float
    ) -> str:
        """Create prompt for LLM verification"""

        prompt = f"""You are a technical content analyzer. Your task is to determine if two topics are similar enough to be merged into one document, or different enough to require separate documents.

**Embedding Similarity Score**: {similarity_score:.3f} (uncertain - needs your judgment)

**NEW TOPIC:**
Title: {new_topic['title']}
Category: {new_topic['category']}
Summary: {new_topic['summary']}

**EXISTING DOCUMENT:**
Title: {existing_document.get('title', 'Unknown')}
Category: {existing_document.get('category', 'Unknown')}
Summary: {existing_document.get('summary', 'No summary available')}

**Instructions:**
1. Analyze if these topics cover the same subject matter or different subjects
2. Consider:
   - Are they about the same technology/concept?
   - Do they target the same use case or different use cases?
   - Would merging them create a coherent document or confuse readers?
   - Is one a subset/superset of the other, or are they complementary?

3. Respond ONLY with this exact JSON format:
{{
  "decision": "merge" or "create",
  "confidence": 0.0 to 1.0,
  "reasoning": "Brief explanation of why merge or create"
}}

**Examples:**
- Topics about "React Hooks" and "useState Hook" → MERGE (subset)
- Topics about "Python Basics" and "Python Advanced" → CREATE (different levels)
- Topics about "Docker Deployment" and "Docker Compose" → MERGE (related tooling)
- Topics about "REST API" and "GraphQL API" → CREATE (different technologies)

Respond with JSON only:"""

        return prompt

    def _parse_llm_response(self, response_text: str, similarity_score: float) -> Dict:
        """
        Parse LLM response and extract decision

        Args:
            response_text: Raw response from LLM
            similarity_score: Original embedding similarity

        Returns:
            Parsed decision dictionary
        """
        import json
        import re

        # Try to extract JSON from response
        try:
            # Remove markdown code blocks if present
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            response_text = response_text.strip()

            # Parse JSON
            llm_decision = json.loads(response_text)

            # Validate required fields
            if "decision" not in llm_decision or "reasoning" not in llm_decision:
                raise ValueError("Missing required fields in LLM response")

            # Normalize decision to lowercase
            action = llm_decision["decision"].lower()
            if action not in ["merge", "create"]:
                raise ValueError(f"Invalid decision: {action}")

            return {
                "action": action,
                "confidence": float(llm_decision.get("confidence", 0.8)),
                "reasoning": llm_decision["reasoning"],
                "original_similarity": similarity_score
            }

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"   ⚠️  Failed to parse LLM response: {e}")
            print(f"   Response: {response_text[:200]}")

            # Fallback: try to extract decision from text
            response_lower = response_text.lower()
            if "merge" in response_lower and "create" not in response_lower:
                action = "merge"
            elif "create" in response_lower:
                action = "create"
            else:
                # Default: if similarity >= 0.65, merge; otherwise create
                action = "merge" if similarity_score >= 0.65 else "create"

            return {
                "action": action,
                "confidence": 0.6,
                "reasoning": f"Parsed from text (fallback parsing)",
                "original_similarity": similarity_score,
                "parse_error": str(e)
            }

    def batch_verify_topics(
        self,
        verify_items: List[Dict],
        rate_limit_delay: float = 1.0
    ) -> Dict:
        """
        Verify multiple uncertain topics using LLM

        Args:
            verify_items: List of items from embedding search results['verify']
                         Each item has: {"topic": {...}, "decision": {...}}
            rate_limit_delay: Delay between LLM calls (seconds)

        Returns:
            Results dictionary:
            {
                "merge": [...],  # Topics that should be merged
                "create": [...], # Topics that should be created
                "total_verified": int,
                "merge_count": int,
                "create_count": int
            }
        """
        import time

        results = {
            "merge": [],
            "create": []
        }

        print(f"\n{'='*80}")
        print(f"🤔 LLM VERIFICATION: {len(verify_items)} uncertain topics")
        print(f"{'='*80}")

        for i, item in enumerate(verify_items, 1):
            topic = item['topic']
            original_decision = item['decision']
            existing_doc = original_decision['target_document']
            similarity = original_decision['similarity']

            print(f"\n[{i}/{len(verify_items)}] Verifying: {topic['title'][:60]}")
            print(f"   Similar to: {existing_doc['title'][:60]}")
            print(f"   Embedding similarity: {similarity:.3f}")

            # Call LLM for verification
            llm_decision = self.verify_topic_similarity(topic, existing_doc, similarity)

            # Print LLM decision
            action_emoji = "🔗" if llm_decision['action'] == "merge" else "✨"
            print(f"   {action_emoji} LLM Decision: {llm_decision['action'].upper()}")
            print(f"   Confidence: {llm_decision['confidence']:.2f}")
            print(f"   Reasoning: {llm_decision['reasoning'][:80]}")

            # Store result
            if llm_decision['action'] == "merge":
                results['merge'].append({
                    'topic': topic,
                    'decision': {
                        'action': 'merge',
                        'target_document': existing_doc,
                        'similarity': similarity,
                        'needs_llm': False,  # Already verified
                        'llm_verified': True,
                        'llm_confidence': llm_decision['confidence'],
                        'llm_reasoning': llm_decision['reasoning'],
                        'reason': f"LLM verified: {llm_decision['reasoning'][:50]}"
                    }
                })
            else:  # create
                results['create'].append({
                    'topic': topic,
                    'decision': {
                        'action': 'create',
                        'target_document': None,
                        'similarity': similarity,
                        'needs_llm': False,  # Already verified
                        'llm_verified': True,
                        'llm_confidence': llm_decision['confidence'],
                        'llm_reasoning': llm_decision['reasoning'],
                        'reason': f"LLM verified: {llm_decision['reasoning'][:50]}"
                    }
                })

            # Rate limiting
            if i < len(verify_items):
                time.sleep(rate_limit_delay)

        # Print summary
        print(f"\n{'='*80}")
        print(f"📊 VERIFICATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total verified: {len(verify_items)}")
        print(f"🔗 Merge (LLM confirmed): {len(results['merge'])}")
        print(f"✨ Create (LLM confirmed): {len(results['create'])}")
        print(f"{'='*80}")

        results['total_verified'] = len(verify_items)
        results['merge_count'] = len(results['merge'])
        results['create_count'] = len(results['create'])

        return results


# Example usage
async def main():
    """Test LLM verifier"""
    print("="*80)
    print("🤔 LLM Verifier Test")
    print("="*80)

    verifier = LLMVerifier()

    # Test case: Similar topics
    new_topic = {
        "title": "Understanding React Hooks",
        "category": "tutorial",
        "summary": "React Hooks are functions that let you use state and other React features in functional components. useState and useEffect are the most common hooks."
    }

    existing_doc = {
        "title": "React Functional Components",
        "category": "tutorial",
        "summary": "Functional components in React are JavaScript functions that return JSX. They can now use hooks to manage state and lifecycle methods."
    }

    decision = verifier.verify_topic_similarity(new_topic, existing_doc, 0.72)

    print(f"\n📊 Test Result:")
    print(f"   Decision: {decision['action'].upper()}")
    print(f"   Confidence: {decision['confidence']:.2f}")
    print(f"   Reasoning: {decision['reasoning']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
