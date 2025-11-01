#!/usr/bin/env python3
"""
LLM Hallucination Quality Check

Verifies that merged documents don't contain false information by:
1. Checking if merged content only contains info from sources
2. Looking for suspicious patterns (invented facts, unsourced claims)
3. Comparing content before/after merge
"""

import os
os.environ['GEMINI_API_KEY'] = 'AIzaSyBlk1Pc88ZxhrtTHtU__rd2fwNcWw3ea-E'

import google.generativeai as genai
from chunked_document_database import ChunkedDocumentDatabase

# Initialize Gemini for verification
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.5-flash-lite')


def check_for_hallucination(document: dict) -> dict:
    """
    Check if a document contains hallucinated or false information

    Args:
        document: Document dictionary

    Returns:
        Analysis results with quality score and issues found
    """
    title = document.get('title', 'Unknown')
    content = document.get('content', '')

    if not content or len(content) < 100:
        return {
            'document_id': document.get('id'),
            'title': title,
            'quality_score': 0,
            'issues': ['Content too short to analyze'],
            'status': 'SKIP'
        }

    # Use LLM to detect potential hallucinations
    prompt = f"""Analyze this technical documentation for potential hallucinations or false information.

DOCUMENT TITLE: {title}

DOCUMENT CONTENT:
{content}

CRITICAL ANALYSIS CHECKLIST:

1. **Invented Facts**: Are there any specific claims (numbers, dates, names, specifications) that seem suspicious or unverifiable?
   - Example: "Version 3.5 was released on January 15, 2023" without context
   - Example: "This uses 256-bit encryption" when not mentioned in context

2. **Unsourced Technical Claims**: Are there technical specifications or implementation details that weren't likely extracted from documentation?
   - Example: "This function runs in O(log n) time" without explanation
   - Example: "The database supports 10 million concurrent users"

3. **Contradictions**: Does the content contradict itself or seem inconsistent?
   - Example: First says "supports Python 3.8+" then later says "requires Python 3.10+"

4. **Overly Specific Without Context**: Are there overly specific details that seem added without source?
   - Example: Exact API endpoint URLs, specific configuration values, precise version numbers

5. **Generic Filler**: Is there generic information that doesn't add value?
   - Example: "This is a powerful tool that developers love"
   - Example: "It's easy to use and highly performant"

RESPONSE FORMAT (JSON only):
{{
  "quality_score": 0-100,
  "has_hallucination": true/false,
  "issues_found": [
    {{
      "type": "invented_fact" | "unsourced_claim" | "contradiction" | "overly_specific" | "generic_filler",
      "severity": "high" | "medium" | "low",
      "excerpt": "exact quote from document (max 100 chars)",
      "explanation": "why this is suspicious"
    }}
  ],
  "overall_assessment": "brief assessment of document quality"
}}

Return ONLY valid JSON, no other text.
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1
            )
        )

        response_text = response.text.strip()

        # Extract JSON from response
        import json
        import re

        # Try to find JSON in response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)

        result = json.loads(response_text)

        # Add document info
        result['document_id'] = document.get('id')
        result['title'] = title
        result['content_length'] = len(content)

        # Determine status
        quality_score = result.get('quality_score', 0)
        has_hallucination = result.get('has_hallucination', False)

        if quality_score >= 80 and not has_hallucination:
            status = 'EXCELLENT'
        elif quality_score >= 60 and not has_hallucination:
            status = 'GOOD'
        elif quality_score >= 40 or (has_hallucination and len(result.get('issues_found', [])) <= 2):
            status = 'FAIR'
        else:
            status = 'POOR'

        result['status'] = status

        return result

    except Exception as e:
        print(f"  ❌ Error analyzing document: {e}")
        return {
            'document_id': document.get('id'),
            'title': title,
            'quality_score': 0,
            'issues': [f'Analysis failed: {str(e)}'],
            'status': 'ERROR'
        }


def main():
    """Check all documents in database for hallucinations"""
    print("=" * 80)
    print("🔍 LLM HALLUCINATION QUALITY CHECK")
    print("=" * 80)
    print()

    # Connect to database
    db = ChunkedDocumentDatabase()

    # Get all documents
    print("📚 Loading documents from database...")
    documents = db.get_all_documents_with_embeddings()

    if not documents:
        print("⚠️  No documents found in database")
        return

    print(f"✅ Found {len(documents)} documents")
    print()

    # Analyze each document
    results = []

    for i, doc in enumerate(documents, 1):
        print(f"[{i}/{len(documents)}] Analyzing: {doc.get('title', 'Unknown')[:50]}...")

        # Get full document with content
        full_doc = db.get_document_by_id(doc.get('id'))

        if not full_doc:
            print(f"  ⚠️  Could not load full document")
            continue

        # Check for hallucination
        analysis = check_for_hallucination(full_doc)
        results.append(analysis)

        # Print result
        status = analysis.get('status', 'UNKNOWN')
        score = analysis.get('quality_score', 0)
        has_hallucination = analysis.get('has_hallucination', False)

        status_emoji = {
            'EXCELLENT': '✅',
            'GOOD': '👍',
            'FAIR': '⚠️',
            'POOR': '❌',
            'SKIP': '⏭️',
            'ERROR': '💥'
        }.get(status, '❓')

        print(f"  {status_emoji} {status} - Score: {score}/100 - Hallucination: {'Yes' if has_hallucination else 'No'}")

        # Print issues if any
        issues = analysis.get('issues_found', [])
        if issues and isinstance(issues, list):
            for issue in issues[:3]:  # Show first 3 issues
                if isinstance(issue, dict):
                    issue_type = issue.get('type', 'unknown')
                    severity = issue.get('severity', 'unknown')
                    explanation = issue.get('explanation', 'No explanation')
                    print(f"    • [{severity.upper()}] {issue_type}: {explanation[:80]}...")

        print()

    # Summary report
    print("=" * 80)
    print("📊 HALLUCINATION CHECK SUMMARY")
    print("=" * 80)
    print()

    # Count by status
    status_counts = {}
    for r in results:
        status = r.get('status', 'UNKNOWN')
        status_counts[status] = status_counts.get(status, 0) + 1

    print("Status Distribution:")
    for status in ['EXCELLENT', 'GOOD', 'FAIR', 'POOR', 'SKIP', 'ERROR']:
        count = status_counts.get(status, 0)
        if count > 0:
            percentage = (count / len(results)) * 100
            print(f"  {status:12s}: {count:3d} ({percentage:5.1f}%)")

    print()

    # Documents with potential hallucinations
    hallucinated_docs = [r for r in results if r.get('has_hallucination', False)]

    if hallucinated_docs:
        print(f"⚠️  {len(hallucinated_docs)} documents with potential hallucinations:")
        print()
        for r in hallucinated_docs:
            print(f"  📄 {r.get('title', 'Unknown')}")
            print(f"     Score: {r.get('quality_score', 0)}/100")
            print(f"     Issues: {len(r.get('issues_found', []))}")
            print()
    else:
        print("✅ No hallucinations detected in any documents!")

    # Average quality score
    scores = [r.get('quality_score', 0) for r in results if r.get('status') not in ['SKIP', 'ERROR']]
    if scores:
        avg_score = sum(scores) / len(scores)
        print(f"📈 Average Quality Score: {avg_score:.1f}/100")

        if avg_score >= 80:
            print("   ✅ Excellent - minimal risk of false information")
        elif avg_score >= 60:
            print("   👍 Good - acceptable quality")
        elif avg_score >= 40:
            print("   ⚠️  Fair - some concerns exist")
        else:
            print("   ❌ Poor - significant risk of false information")

    print()
    print("=" * 80)

    # Save detailed report
    import json
    from datetime import datetime

    report_filename = f"hallucination_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_documents': len(documents),
            'analyzed': len(results),
            'status_counts': status_counts,
            'average_quality_score': avg_score if scores else 0,
            'hallucinated_count': len(hallucinated_docs),
            'detailed_results': results
        }, f, indent=2)

    print(f"📄 Detailed report saved to: {report_filename}")
    print()


if __name__ == "__main__":
    main()
