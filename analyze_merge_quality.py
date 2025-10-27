#!/usr/bin/env python3
"""
Analyze database quality and check for unmerged topics
"""

import sys
import psycopg2
from datetime import datetime

def main():
    print("=" * 80)
    print("DATABASE QUALITY & MERGE ANALYSIS")
    print("=" * 80)
    print()

    try:
        # Connect to database
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="crawl4ai",
            user="postgres",
            password="postgres"
        )
        cursor = conn.cursor()

        # Get all documents with their chunks
        print("📊 LOADING ALL DOCUMENTS...")
        cursor.execute("""
            SELECT
                d.id,
                d.title,
                d.summary,
                LENGTH(d.content) as content_length,
                array_length(d.keywords, 1) as keyword_count,
                d.created_at,
                d.updated_at,
                COUNT(c.id) as chunk_count
            FROM documents d
            LEFT JOIN chunks c ON c.document_id = d.id
            GROUP BY d.id, d.title, d.summary, d.content, d.keywords, d.created_at, d.updated_at
            ORDER BY d.updated_at DESC NULLS LAST
        """)

        documents = cursor.fetchall()
        print(f"   Found {len(documents)} documents\n")

        # Quality analysis
        print("=" * 80)
        print("DOCUMENT QUALITY RATINGS")
        print("=" * 80)
        print()

        high_quality = []
        medium_quality = []
        low_quality = []

        for doc in documents:
            doc_id, title, summary, content_len, keyword_count, created_at, updated_at, chunk_count = doc

            # Calculate quality score
            score = 0
            issues = []

            # Content length scoring
            if content_len >= 2000:
                score += 3
            elif content_len >= 1000:
                score += 2
            elif content_len >= 500:
                score += 1
            else:
                issues.append(f"Short content ({content_len} chars)")

            # Chunk count scoring
            if chunk_count >= 3:
                score += 2
            elif chunk_count >= 2:
                score += 1
            else:
                issues.append(f"Only {chunk_count} chunk(s)")

            # Keywords scoring
            keyword_count = keyword_count or 0
            if keyword_count >= 10:
                score += 2
            elif keyword_count >= 5:
                score += 1
            else:
                issues.append(f"Few keywords ({keyword_count})")

            # Summary check
            if summary and len(summary) >= 100:
                score += 1

            # Check if merged (updated after creation)
            was_merged = updated_at != created_at if (updated_at and created_at) else False

            # Classify quality
            if score >= 6:
                quality = "🟢 HIGH"
                high_quality.append(doc)
            elif score >= 4:
                quality = "🟡 MEDIUM"
                medium_quality.append(doc)
            else:
                quality = "🔴 LOW"
                low_quality.append(doc)

            # Print document info
            print(f"{quality} (Score: {score}/8)")
            print(f"   Title: {title[:70]}...")
            print(f"   Content: {content_len:,} chars | Chunks: {chunk_count} | Keywords: {keyword_count}")
            if was_merged:
                print(f"   🔄 Merged document (updated after creation)")
            if issues:
                print(f"   ⚠️  Issues: {', '.join(issues)}")
            print()

        # Summary statistics
        total = len(documents)
        print("=" * 80)
        print("QUALITY SUMMARY")
        print("=" * 80)
        print(f"Total Documents: {total}")
        print()
        print(f"🟢 High Quality:   {len(high_quality):2d} ({len(high_quality)/total*100:.1f}%)")
        print(f"🟡 Medium Quality: {len(medium_quality):2d} ({len(medium_quality)/total*100:.1f}%)")
        print(f"🔴 Low Quality:    {len(low_quality):2d} ({len(low_quality)/total*100:.1f}%)")
        print()

        # Check merge history
        print("=" * 80)
        print("MERGE HISTORY ANALYSIS")
        print("=" * 80)
        print()

        cursor.execute("""
            SELECT
                target_doc_id,
                source_topic_title,
                merge_strategy,
                changes_made,
                merged_at
            FROM merge_history
            ORDER BY merged_at DESC
        """)

        merges = cursor.fetchall()
        print(f"Total merge operations: {len(merges)}")
        print()

        if merges:
            print("Recent merges (last 10):")
            for merge in merges[:10]:
                target_id, topic_title, strategy, changes, merged_at = merge
                print(f"\n📝 {merged_at}")
                print(f"   Topic: {topic_title[:60]}...")
                print(f"   Strategy: {strategy}")
                print(f"   Changes: {changes[:80]}...")

        print()
        print()

        # Check for topics that might not have merged
        print("=" * 80)
        print("UNMERGED TOPICS ANALYSIS")
        print("=" * 80)
        print()

        # Look for documents with only 1 chunk and no merge history
        cursor.execute("""
            SELECT
                d.id,
                d.title,
                d.created_at,
                d.updated_at,
                COUNT(c.id) as chunk_count,
                COUNT(m.id) as merge_count
            FROM documents d
            LEFT JOIN chunks c ON c.document_id = d.id
            LEFT JOIN merge_history m ON m.target_doc_id = d.id
            GROUP BY d.id, d.title, d.created_at, d.updated_at
            HAVING COUNT(c.id) = 1 AND COUNT(m.id) = 0
            ORDER BY d.created_at DESC
        """)

        unmerged_candidates = cursor.fetchall()

        if unmerged_candidates:
            print(f"Found {len(unmerged_candidates)} documents that might be standalone topics:")
            print()
            for doc in unmerged_candidates:
                doc_id, title, created_at, updated_at, chunk_count, merge_count = doc
                print(f"📄 {title[:70]}...")
                print(f"   ID: {doc_id[:50]}...")
                print(f"   Created: {created_at}")
                print(f"   Chunks: {chunk_count}")
                print(f"   Never merged into another document")

                # Check if this document has content
                cursor.execute("""
                    SELECT LENGTH(content), array_length(keywords, 1)
                    FROM documents WHERE id = %s
                """, (doc_id,))
                content_info = cursor.fetchone()
                if content_info:
                    content_len, kw_count = content_info
                    print(f"   Content: {content_len} chars | Keywords: {kw_count or 0}")
                print()

        else:
            print("✅ No obvious unmerged standalone topics found")
            print("   All single-chunk documents have been used as merge targets")
            print()

        # Check for potential merge issues
        print("=" * 80)
        print("POTENTIAL MERGE ISSUES")
        print("=" * 80)
        print()

        # Documents that were created recently but never merged
        cursor.execute("""
            SELECT
                d.id,
                d.title,
                LENGTH(d.content) as content_len,
                d.created_at,
                COUNT(m.id) as times_merged_into
            FROM documents d
            LEFT JOIN merge_history m ON m.target_doc_id = d.id
            GROUP BY d.id, d.title, d.content, d.created_at
            HAVING COUNT(m.id) = 0
            ORDER BY d.created_at DESC
            LIMIT 5
        """)

        never_merged = cursor.fetchall()

        if never_merged:
            print(f"Documents that have NEVER been merge targets (latest 5):")
            print()
            for doc in never_merged:
                doc_id, title, content_len, created_at, merge_count = doc
                print(f"📄 {title[:70]}...")
                print(f"   Content: {content_len:,} chars")
                print(f"   Created: {created_at}")
                print(f"   Reason: Likely a base document or too unique to merge with others")
                print()

        # Analysis of why topics might not merge
        print("=" * 80)
        print("WHY TOPICS DON'T MERGE")
        print("=" * 80)
        print()

        print("Possible reasons a topic wasn't merged:")
        print()
        print("1. 🎯 **Too Unique** (similarity < 0.4)")
        print("   - Topic content is significantly different from all existing docs")
        print("   - Creates a new standalone document instead")
        print()
        print("2. 🤔 **Uncertain Match** (0.4 < similarity < 0.85)")
        print("   - LLM verification determines they shouldn't merge")
        print("   - Content overlap isn't strong enough")
        print()
        print("3. 📝 **First Document** (no existing docs to merge with)")
        print("   - First topic on a subject becomes base document")
        print("   - Future similar topics merge into it")
        print()
        print("4. ⚠️  **Processing Error**")
        print("   - Network issues during embedding generation")
        print("   - LLM API failures")
        print("   - Database transaction rollbacks")
        print()

        # Get similarity distribution from merge history
        cursor.execute("""
            SELECT merge_strategy, COUNT(*)
            FROM merge_history
            GROUP BY merge_strategy
        """)
        strategies = cursor.fetchall()

        if strategies:
            print("Merge strategies used:")
            for strategy, count in strategies:
                print(f"   {strategy}: {count} merges")
            print()

        cursor.close()
        conn.close()

        # Final recommendation
        print("=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print()

        if len(low_quality) > 0:
            print("⚠️  ACTION NEEDED:")
            print(f"   - {len(low_quality)} low-quality documents found")
            print("   - Consider crawling more related pages to enrich these docs")
            print()

        if len(high_quality) / total >= 0.5:
            print("✅ GOOD: 50%+ documents are high quality")
            print("   - Merge strategy is working well")
            print("   - Documents are being enriched properly")
        else:
            print("⚠️  IMPROVEMENT NEEDED:")
            print("   - Less than 50% are high quality")
            print("   - Consider:")
            print("     • Crawling more pages per topic")
            print("     • Lowering merge threshold for more aggressive merging")
            print("     • Crawling related documentation sections")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
