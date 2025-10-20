#!/usr/bin/env python3
"""
Document Merger Module

Merges new topics with existing documents.
Supports two modes: paragraph and full-doc
"""

import os

# Suppress gRPC warnings (must be set BEFORE importing genai)
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

from typing import List, Dict, Optional
import google.generativeai as genai
from datetime import datetime


class DocumentMerger:
    """
    Merges topics with existing documents using LLM
    Supports two modes: paragraph and full-doc
    """

    def __init__(self, api_key: str = None):
        """
        Initialize document merger

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Please set it in .env file")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')

        print("✅ Document merger initialized")
        print(f"   Model: gemini-2.5-flash-lite")

    def merge_paragraph_document(
        self,
        topic: Dict,
        existing_document: Dict
    ) -> Dict:
        """
        Merge topic with existing paragraph document

        Args:
            topic: New topic to merge
            existing_document: Existing paragraph document

        Returns:
            Updated document dictionary
        """
        prompt = f"""Merge this new topic information into the existing paragraph document.

EXISTING DOCUMENT:
Title: {existing_document['title']}
Content: {existing_document['content']}

NEW TOPIC TO MERGE:
Title: {topic['title']}
Summary: {topic['summary']}
Description: {topic['description']}

Instructions:
1. Create a single, well-integrated paragraph that combines BOTH the existing content and new information
2. Avoid redundancy - merge similar points smoothly
3. Keep the paragraph concise but comprehensive (6-12 sentences)
4. Maintain professional tone
5. Do NOT include title or headings
6. Ensure all important information from BOTH sources is included

Output only the merged paragraph text, nothing else.
"""

        try:
            print(f"\n  🔀 Merging paragraph for: {topic['title']} → {existing_document['title']}")

            response = self.model.generate_content(prompt)
            merged_content = response.text.strip()

            updated_document = {
                "title": existing_document['title'],
                "category": existing_document.get('category', topic['category']),
                "mode": "paragraph",
                "content": merged_content,
                "created_at": existing_document.get('created_at', datetime.now().isoformat()),
                "updated_at": datetime.now().isoformat(),
                "merged_topics": existing_document.get('merged_topics', []) + [{
                    "title": topic['title'],
                    "merged_at": datetime.now().isoformat()
                }]
            }

            print(f"  ✅ Paragraph merged ({len(merged_content)} chars)")
            return updated_document

        except Exception as e:
            print(f"  ❌ Error merging paragraph: {e}")
            return None

    def merge_fulldoc_document(
        self,
        topic: Dict,
        existing_document: Dict
    ) -> Dict:
        """
        Merge topic with existing full document

        Args:
            topic: New topic to merge
            existing_document: Existing full document

        Returns:
            Updated document dictionary
        """
        prompt = f"""Merge this new topic information into the existing full document.

EXISTING DOCUMENT:
Title: {existing_document['title']}
Content:
{existing_document['content']}

NEW TOPIC TO MERGE:
Title: {topic['title']}
Summary: {topic['summary']}
Description: {topic['description']}

Instructions:
1. Carefully read both the existing document and new topic information
2. Identify where the new information fits best in the existing structure
3. Merge the new information seamlessly into appropriate sections
4. If needed, create new sections or subsections for new information
5. Maintain consistent markdown formatting:
   - Use ## for main sections
   - Use ### for subsections
   - Use bullet points and numbered lists appropriately
   - Use **bold** for emphasis
   - Use `code` formatting for technical terms
6. Avoid redundancy - merge similar information smoothly
7. Keep the document well-organized and comprehensive
8. Do NOT include the main title (# Title) - start with sections
9. Ensure ALL important information from BOTH sources is included

Output the complete merged markdown document.
"""

        try:
            print(f"\n  🔀 Merging full document for: {topic['title']} → {existing_document['title']}")

            response = self.model.generate_content(prompt)
            merged_content = response.text.strip()

            updated_document = {
                "title": existing_document['title'],
                "category": existing_document.get('category', topic['category']),
                "mode": "full-doc",
                "content": merged_content,
                "created_at": existing_document.get('created_at', datetime.now().isoformat()),
                "updated_at": datetime.now().isoformat(),
                "merged_topics": existing_document.get('merged_topics', []) + [{
                    "title": topic['title'],
                    "merged_at": datetime.now().isoformat()
                }]
            }

            print(f"  ✅ Full document merged ({len(merged_content)} chars)")
            return updated_document

        except Exception as e:
            print(f"  ❌ Error merging full document: {e}")
            return None

    def merge_document(
        self,
        topic: Dict,
        existing_document: Dict,
        mode: str = "paragraph"
    ) -> Dict:
        """
        Merge topic with existing document in specified mode

        Args:
            topic: New topic to merge
            existing_document: Existing document
            mode: "paragraph" or "full-doc"

        Returns:
            Updated document dictionary
        """
        if mode == "paragraph":
            return self.merge_paragraph_document(topic, existing_document)
        elif mode == "full-doc":
            return self.merge_fulldoc_document(topic, existing_document)
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'paragraph' or 'full-doc'")

    def merge_documents_batch(
        self,
        merge_pairs: List[Dict],
        mode: str = "paragraph"
    ) -> Dict:
        """
        Merge multiple topic-document pairs in batch

        Args:
            merge_pairs: List of dicts with 'topic' and 'existing_document'
            mode: "paragraph" or "full-doc"

        Returns:
            Results dictionary with merged documents and statistics
        """
        print(f"\n{'='*80}")
        print(f"🔀 BATCH DOCUMENT MERGING ({mode.upper()} mode)")
        print(f"{'='*80}")
        print(f"Pairs to merge: {len(merge_pairs)}")

        merged_documents = []
        failed = []

        for i, pair in enumerate(merge_pairs, 1):
            topic = pair['topic']
            existing_doc = pair['existing_document']

            print(f"\n[{i}/{len(merge_pairs)}] Processing merge:")
            print(f"   Topic: {topic['title']}")
            print(f"   Document: {existing_doc['title']}")

            merged_doc = self.merge_document(topic, existing_doc, mode)

            if merged_doc:
                merged_documents.append(merged_doc)
            else:
                failed.append(f"{topic['title']} → {existing_doc['title']}")

        # Print summary
        self._print_batch_summary(merged_documents, failed, mode)

        return {
            "mode": mode,
            "merged_documents": merged_documents,
            "failed": failed,
            "success_count": len(merged_documents),
            "fail_count": len(failed),
            "total": len(merge_pairs)
        }

    def merge_documents_both_modes(
        self,
        merge_pairs: List[Dict]
    ) -> Dict:
        """
        Merge documents in BOTH modes for each pair

        Args:
            merge_pairs: List of dicts with 'topic', 'para_document', and 'fulldoc_document'

        Returns:
            Results dictionary with both paragraph and full-doc merged versions
        """
        print(f"\n{'='*80}")
        print(f"🔀 MERGING DOCUMENTS IN BOTH MODES")
        print(f"{'='*80}")
        print(f"Pairs to merge: {len(merge_pairs)}")
        print(f"Total merges: {len(merge_pairs) * 2}")

        merged_paragraph = []
        merged_fulldoc = []
        failed = []

        for i, pair in enumerate(merge_pairs, 1):
            topic = pair['topic']

            print(f"\n{'='*80}")
            print(f"[{i}/{len(merge_pairs)}] Processing: {topic['title']}")
            print(f"{'='*80}")

            # Merge paragraph version
            if 'para_document' in pair and pair['para_document']:
                print(f"\n  🔹 MODE 1: Paragraph")
                para_merged = self.merge_paragraph_document(topic, pair['para_document'])
                if para_merged:
                    merged_paragraph.append(para_merged)
                else:
                    failed.append(f"{topic['title']} → {pair['para_document']['title']} (paragraph)")

            # Merge full-doc version
            if 'fulldoc_document' in pair and pair['fulldoc_document']:
                print(f"\n  🔹 MODE 2: Full Document")
                full_merged = self.merge_fulldoc_document(topic, pair['fulldoc_document'])
                if full_merged:
                    merged_fulldoc.append(full_merged)
                else:
                    failed.append(f"{topic['title']} → {pair['fulldoc_document']['title']} (full-doc)")

        # Print summary
        self._print_both_modes_summary(merged_paragraph, merged_fulldoc, failed, len(merge_pairs))

        return {
            "merged_paragraph": merged_paragraph,
            "merged_fulldoc": merged_fulldoc,
            "failed": failed,
            "paragraph_count": len(merged_paragraph),
            "fulldoc_count": len(merged_fulldoc),
            "fail_count": len(failed),
            "total_pairs": len(merge_pairs),
            "total_merged": len(merged_paragraph) + len(merged_fulldoc)
        }

    def _print_batch_summary(self, merged: List[Dict], failed: List[str], mode: str):
        """Print batch merge summary"""
        print(f"\n{'='*80}")
        print(f"📊 BATCH MERGE SUMMARY ({mode.upper()})")
        print(f"{'='*80}")

        print(f"\n✅ Success: {len(merged)}")
        if merged:
            for doc in merged:
                merge_count = len(doc.get('merged_topics', []))
                print(f"   • {doc['title']} ({len(doc['content'])} chars, {merge_count} topics merged)")

        if failed:
            print(f"\n❌ Failed: {len(failed)}")
            for pair in failed:
                print(f"   • {pair}")

        print(f"\n{'='*80}")

    def _print_both_modes_summary(
        self,
        merged_para: List[Dict],
        merged_full: List[Dict],
        failed: List[str],
        total_pairs: int
    ):
        """Print summary for both modes merge"""
        print(f"\n{'='*80}")
        print(f"📊 DUAL-MODE MERGE SUMMARY")
        print(f"{'='*80}")

        print(f"\nPairs processed: {total_pairs}")
        print(f"Total documents merged: {len(merged_para) + len(merged_full)}")

        print(f"\n📝 PARAGRAPH MODE: {len(merged_para)} documents")
        if merged_para:
            for doc in merged_para:
                merge_count = len(doc.get('merged_topics', []))
                print(f"   • {doc['title']} ({len(doc['content'])} chars, {merge_count} topics)")

        print(f"\n📄 FULL-DOC MODE: {len(merged_full)} documents")
        if merged_full:
            for doc in merged_full:
                merge_count = len(doc.get('merged_topics', []))
                print(f"   • {doc['title']} ({len(doc['content'])} chars, {merge_count} topics)")

        if failed:
            print(f"\n❌ FAILED: {len(failed)}")
            for pair in failed:
                print(f"   • {pair}")

        print(f"\n{'='*80}")

    def save_merged_documents(self, results: Dict, output_dir: str = "merged_documents", save_to_db: bool = True, db_path: str = "documents.db"):
        """
        Save merged documents to files and update in vector database

        Args:
            results: Results from merge_documents_batch or merge_documents_both_modes
            output_dir: Output directory for markdown files
            save_to_db: Whether to update in vector database
            db_path: Path to database file
        """
        import json
        from pathlib import Path

        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Determine what type of results we have
        if "merged_paragraph" in results:
            # Both modes
            all_docs = results["merged_paragraph"] + results["merged_fulldoc"]
        else:
            # Single mode
            all_docs = results["merged_documents"]

        # Update in vector database if enabled
        if save_to_db:
            print(f"\n💾 Updating {len(all_docs)} documents in vector database...")
            try:
                from document_database import DocumentDatabase
                db = DocumentDatabase(db_path=db_path)

                success_count = 0
                for doc in all_docs:
                    if db.update_document(doc):
                        success_count += 1

                print(f"  ✅ Updated {success_count}/{len(all_docs)} documents in database")

                # Print statistics
                db.print_statistics()

            except Exception as e:
                print(f"  ❌ Database update error: {e}")

        # Save each document as markdown
        for doc in all_docs:
            # Create safe filename
            safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_'
                                for c in doc['title'])
            safe_title = safe_title.replace(' ', '_').lower()

            filename = f"{safe_title}_{doc['mode']}_merged.md"
            filepath = Path(output_dir) / filename

            # Write document
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {doc['title']}\n\n")
                f.write(f"**Category**: {doc['category']}\n")
                f.write(f"**Mode**: {doc['mode']}\n")
                f.write(f"**Created**: {doc.get('created_at', 'N/A')}\n")
                f.write(f"**Updated**: {doc.get('updated_at', 'N/A')}\n")

                # List merged topics
                if 'merged_topics' in doc and doc['merged_topics']:
                    f.write(f"**Merged Topics**: {len(doc['merged_topics'])}\n")
                    for mt in doc['merged_topics']:
                        f.write(f"  - {mt['title']} (merged: {mt['merged_at']})\n")

                f.write("\n---\n\n")
                f.write(doc['content'])
                f.write("\n")

        # Save summary as JSON
        summary_file = Path(output_dir) / "merge_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n📁 Markdown files saved to: {output_dir}/")
        print(f"   Files: {len(all_docs)}")
        print(f"   Summary: merge_summary.json")


# Example usage and testing
async def main():
    """Test document merger with isolated examples"""
    print("="*80)
    print("🔀 Document Merger Test (Isolated)")
    print("="*80)

    # Initialize merger
    try:
        merger = DocumentMerger()
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        return

    # Example existing documents
    existing_para_doc = {
        "title": "Python Bug Reporting",
        "category": "guide",
        "mode": "paragraph",
        "content": "To report bugs in Python, use the GitHub issues tracker at https://github.com/python/cpython/issues. Search existing issues first to avoid duplicates. When creating a new issue, provide a clear title under 10 words and a detailed description including expected vs actual behavior.",
        "created_at": "2025-10-20T10:00:00"
    }

    existing_full_doc = {
        "title": "Python Bug Reporting",
        "category": "guide",
        "mode": "full-doc",
        "content": """## Overview

The Python bug reporting system uses GitHub Issues for tracking bugs and feature requests.

## Before Reporting

1. Search the existing issues
2. Check if it's already been reported
3. Gather all relevant information

## How to Report

Visit https://github.com/python/cpython/issues and click "New Issue". Provide:
- Clear title (under 10 words)
- Detailed description
- Steps to reproduce
- Expected vs actual behavior
""",
        "created_at": "2025-10-20T10:00:00"
    }

    # Example new topic to merge
    new_topic = {
        "title": "Reporting Python Bugs - Additional Info",
        "category": "guide",
        "summary": "Additional information about the Python bug reporting process, including platform details and extension modules.",
        "description": "When reporting bugs, always include your platform details: Python version (use python --version), Operating System (name and version), and hardware architecture. If using extension modules, list their names and versions. Anonymous reports are not allowed - you must have a GitHub account. After submitting, you'll receive updates on your report as developers review it."
    }

    # Test 1: Merge paragraph document
    print("\n" + "="*80)
    print("TEST 1: MERGE PARAGRAPH DOCUMENT")
    print("="*80)

    merge_pairs_para = [{
        'topic': new_topic,
        'existing_document': existing_para_doc
    }]

    para_results = merger.merge_documents_batch(merge_pairs_para, mode="paragraph")

    # Test 2: Merge full document
    print("\n" + "="*80)
    print("TEST 2: MERGE FULL DOCUMENT")
    print("="*80)

    merge_pairs_full = [{
        'topic': new_topic,
        'existing_document': existing_full_doc
    }]

    full_results = merger.merge_documents_batch(merge_pairs_full, mode="full-doc")

    # Test 3: Merge both modes
    print("\n" + "="*80)
    print("TEST 3: MERGE BOTH MODES")
    print("="*80)

    merge_pairs_both = [{
        'topic': new_topic,
        'para_document': existing_para_doc,
        'fulldoc_document': existing_full_doc
    }]

    both_results = merger.merge_documents_both_modes(merge_pairs_both)

    # Save merged documents
    merger.save_merged_documents(both_results, output_dir="test_merged_documents")

    # Show before/after comparison
    print("\n" + "="*80)
    print("📊 BEFORE/AFTER COMPARISON")
    print("="*80)

    if both_results['merged_paragraph']:
        print("\n📝 PARAGRAPH MODE:")
        print(f"   BEFORE: {len(existing_para_doc['content'])} chars")
        print(f"   AFTER:  {len(both_results['merged_paragraph'][0]['content'])} chars")
        print(f"   CHANGE: +{len(both_results['merged_paragraph'][0]['content']) - len(existing_para_doc['content'])} chars")

    if both_results['merged_fulldoc']:
        print("\n📄 FULL-DOC MODE:")
        print(f"   BEFORE: {len(existing_full_doc['content'])} chars")
        print(f"   AFTER:  {len(both_results['merged_fulldoc'][0]['content'])} chars")
        print(f"   CHANGE: +{len(both_results['merged_fulldoc'][0]['content']) - len(existing_full_doc['content'])} chars")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
