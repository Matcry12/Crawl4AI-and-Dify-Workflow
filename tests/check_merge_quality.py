#!/usr/bin/env python3
"""Check the quality of merged documents after workflow execution"""

import os
import sys
import asyncio
from datetime import datetime

async def main():
    print("=" * 80)
    print("MERGE & CREATE QUALITY CHECK")
    print("=" * 80)
    print()

    try:
        from chunked_document_database import SimpleDocumentDatabase

        # Initialize database
        db = SimpleDocumentDatabase()
        print("✅ Connected to database")
        print()

        # Get all documents with their chunks
        print("📊 Loading all documents with chunks...")
        documents = db.get_all_documents_with_embeddings()
        print(f"   Found {len(documents)} documents")
        print()

        # Analyze each document
        print("=" * 80)
        print("DOCUMENT QUALITY ANALYSIS")
        print("=" * 80)
        print()

        high_quality = 0
        medium_quality = 0
        low_quality = 0

        for i, doc in enumerate(documents, 1):
            doc_id = doc['id']

            # Get full document with chunks
            full_doc = db.get_document_by_id(doc_id)

            if not full_doc:
                print(f"⚠️  Document {i}: Could not load full document {doc_id}")
                continue

            # Extract metrics
            title = full_doc.get('title', 'No title')
            content = full_doc.get('content', '')
            summary = full_doc.get('summary', '')
            keywords = full_doc.get('keywords', [])
            chunks = full_doc.get('chunks', [])
            created_at = full_doc.get('created_at', '')
            updated_at = full_doc.get('updated_at', '')

            content_length = len(content)
            num_chunks = len(chunks)
            num_keywords = len(keywords)
            has_summary = len(summary) > 0

            # Quality assessment
            quality_score = 0
            issues = []

            # Content length check
            if content_length >= 2000:
                quality_score += 3
            elif content_length >= 1000:
                quality_score += 2
            elif content_length >= 500:
                quality_score += 1
            else:
                issues.append(f"Short content ({content_length} chars)")

            # Chunk count check
            if num_chunks >= 3:
                quality_score += 2
            elif num_chunks >= 2:
                quality_score += 1
            else:
                issues.append(f"Only {num_chunks} chunk(s)")

            # Keywords check
            if num_keywords >= 10:
                quality_score += 2
            elif num_keywords >= 5:
                quality_score += 1
            else:
                issues.append(f"Few keywords ({num_keywords})")

            # Summary check
            if has_summary and len(summary) >= 100:
                quality_score += 1
            elif not has_summary:
                issues.append("No summary")

            # Check if document was recently updated (merged)
            was_updated = updated_at != created_at if updated_at and created_at else False

            # Classify quality
            if quality_score >= 6:
                quality = "🟢 HIGH"
                high_quality += 1
            elif quality_score >= 4:
                quality = "🟡 MEDIUM"
                medium_quality += 1
            else:
                quality = "🔴 LOW"
                low_quality += 1

            # Print document info
            print(f"[{i}/{len(documents)}] {quality} (Score: {quality_score}/8)")
            print(f"   Title: {title[:70]}...")
            print(f"   Content: {content_length} chars")
            print(f"   Chunks: {num_chunks}")
            print(f"   Keywords: {num_keywords}")
            print(f"   Summary: {'✓' if has_summary else '✗'}")

            if was_updated:
                print(f"   🔄 Recently merged/updated")

            if issues:
                print(f"   ⚠️  Issues: {', '.join(issues)}")

            # Show chunk details
            if chunks:
                print(f"   📦 Chunk breakdown:")
                for j, chunk in enumerate(chunks[:5], 1):  # Show first 5 chunks
                    chunk_content = chunk.get('content', '')
                    chunk_len = len(chunk_content)
                    print(f"      [{j}] {chunk_len} chars: {chunk_content[:60]}...")
                if len(chunks) > 5:
                    print(f"      ... and {len(chunks) - 5} more chunks")

            print()

        # Summary statistics
        print("=" * 80)
        print("QUALITY SUMMARY")
        print("=" * 80)
        total = len(documents)

        print(f"Total Documents: {total}")
        print()
        print(f"🟢 High Quality:   {high_quality:2d} ({high_quality/total*100:.1f}%)")
        print(f"🟡 Medium Quality: {medium_quality:2d} ({medium_quality/total*100:.1f}%)")
        print(f"🔴 Low Quality:    {low_quality:2d} ({low_quality/total*100:.1f}%)")
        print()

        # Quality criteria explanation
        print("Quality Criteria:")
        print("  High (6-8 points):")
        print("    • Content ≥2000 chars (3 pts) or ≥1000 chars (2 pts)")
        print("    • Chunks ≥3 (2 pts) or ≥2 (1 pt)")
        print("    • Keywords ≥10 (2 pts) or ≥5 (1 pt)")
        print("    • Summary ≥100 chars (1 pt)")
        print()
        print("  Medium (4-5 points):")
        print("    • Moderate content and chunk coverage")
        print()
        print("  Low (0-3 points):")
        print("    • Short content, few chunks, insufficient metadata")
        print()

        # Check merge history
        print("=" * 80)
        print("MERGE HISTORY CHECK")
        print("=" * 80)
        print()

        try:
            # Query merge history using database's connection method
            import psycopg2
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="crawl4ai",
                user="crawl4ai_user",
                password="crawl4ai_password"
            )
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) FROM merge_history
            """)
            merge_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT
                    target_doc_id,
                    merged_at,
                    merge_strategy,
                    changes_summary
                FROM merge_history
                ORDER BY merged_at DESC
                LIMIT 10
            """)
            recent_merges = cursor.fetchall()

            cursor.close()
            conn.close()

            print(f"Total merges in history: {merge_count}")
            print()

            if recent_merges:
                print("Recent merges (last 10):")
                for merge in recent_merges:
                    target_id, merged_at, strategy, changes = merge
                    print(f"   • {merged_at}")
                    print(f"     Target: {target_id[:40]}...")
                    print(f"     Strategy: {strategy}")
                    print(f"     Changes: {changes[:100]}...")
                    print()
        except Exception as e:
            print(f"⚠️  Could not query merge history: {e}")
            merge_count = 0

        # Overall assessment
        print("=" * 80)
        print("OVERALL ASSESSMENT")
        print("=" * 80)

        if high_quality / total >= 0.6:
            print("✅ EXCELLENT: Most documents are high quality")
        elif high_quality / total >= 0.4:
            print("✅ GOOD: Many documents are high quality")
        elif medium_quality / total >= 0.5:
            print("⚠️  FAIR: Documents need more content/merges")
        else:
            print("❌ POOR: Most documents are low quality")

        print()
        print(f"Average quality score: {(high_quality*7 + medium_quality*4.5 + low_quality*2)/total:.1f}/8")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
