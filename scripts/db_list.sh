#!/bin/bash
# List all documents with their chunk counts

echo "📚 All Documents"
echo "════════════════════════════════════════════════════════════════"

docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    LEFT(d.id, 40) as id,
    LEFT(d.title, 30) as title,
    d.mode,
    COUNT(DISTINCT s.id) as sections,
    COUNT(DISTINCT p.id) as props
FROM documents d
LEFT JOIN semantic_sections s ON s.document_id = d.id
LEFT JOIN semantic_propositions p ON p.section_id = s.id
GROUP BY d.id, d.title, d.mode
ORDER BY d.created_at DESC;
"
