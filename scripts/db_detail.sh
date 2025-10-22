#!/bin/bash
# Show detailed information about a specific document

if [ $# -eq 0 ]; then
    echo "Usage: $0 <document_id>"
    echo ""
    echo "Available documents:"
    docker exec docker-db-1 psql -U postgres -d crawl4ai -t -c "SELECT id FROM documents ORDER BY created_at DESC LIMIT 10;"
    exit 1
fi

DOC_ID="$1"

echo "📄 Document Details: $DOC_ID"
echo "════════════════════════════════════════════════════════════════"

# Document info
echo ""
echo "📋 Basic Info"
echo "────────────────────────────────────────────────────────────────"
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    id,
    title,
    mode,
    category,
    LENGTH(content) as content_length,
    created_at,
    updated_at
FROM documents
WHERE id = '$DOC_ID';
"

# Sections
echo ""
echo "📑 Sections"
echo "────────────────────────────────────────────────────────────────"
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    s.section_index,
    COALESCE(s.header, '(no header)') as header,
    LENGTH(s.content) as content_length,
    COUNT(p.id) as proposition_count
FROM semantic_sections s
LEFT JOIN semantic_propositions p ON p.section_id = s.id
WHERE s.document_id = '$DOC_ID'
GROUP BY s.id, s.section_index, s.header, s.content
ORDER BY s.section_index;
"

# Propositions
echo ""
echo "💬 Propositions"
echo "────────────────────────────────────────────────────────────────"
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    s.section_index,
    p.proposition_index,
    LEFT(p.content, 80) || '...' as content_preview,
    p.proposition_type
FROM semantic_propositions p
JOIN semantic_sections s ON p.section_id = s.id
WHERE s.document_id = '$DOC_ID'
ORDER BY s.section_index, p.proposition_index
LIMIT 20;
"

# Embeddings
echo ""
echo "🔢 Embeddings"
echo "────────────────────────────────────────────────────────────────"
docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    entity_type,
    COUNT(*) as count,
    jsonb_array_length(embedding) as dimensions
FROM embeddings
WHERE
    entity_id = '$DOC_ID' OR
    entity_id IN (SELECT id FROM semantic_sections WHERE document_id = '$DOC_ID') OR
    entity_id IN (SELECT p.id FROM semantic_propositions p JOIN semantic_sections s ON p.section_id = s.id WHERE s.document_id = '$DOC_ID')
GROUP BY entity_type, jsonb_array_length(embedding);
"

echo "════════════════════════════════════════════════════════════════"
