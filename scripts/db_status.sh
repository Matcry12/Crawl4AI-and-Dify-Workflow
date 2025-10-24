#!/bin/bash
# Quick database status check

echo "📊 Database Status"
echo "════════════════════════════════════════════════"

docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -t -A -F'|' -c "
SELECT
    (SELECT COUNT(*) FROM documents) as documents,
    (SELECT COUNT(*) FROM semantic_sections) as sections,
    (SELECT COUNT(*) FROM semantic_propositions) as propositions,
    (SELECT COUNT(*) FROM embeddings) as embeddings;
" | while IFS='|' read docs sections props embeddings; do
    echo "Documents:     $docs"
    echo "Sections:      $sections"
    echo "Propositions:  $props"
    echo "Embeddings:    $embeddings"
done

echo ""
echo "📈 Coverage"
echo "────────────────────────────────────────────────"

docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -t -c "
SELECT
    COUNT(DISTINCT d.id) as total_docs,
    COUNT(DISTINCT CASE WHEN s.id IS NOT NULL THEN d.id END) as docs_with_chunks,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN s.id IS NOT NULL THEN d.id END) / COUNT(DISTINCT d.id), 1) as coverage_pct
FROM documents d
LEFT JOIN semantic_sections s ON s.document_id = d.id;
" | tail -1 | while read total with_chunks pct; do
    echo "Documents with chunks: $with_chunks / $total ($pct%)"
done

echo ""
echo "💾 Database Size"
echo "────────────────────────────────────────────────"

docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -t -c "
SELECT pg_size_pretty(pg_database_size('crawl4ai')) as size;
" | tail -1

echo "════════════════════════════════════════════════"
