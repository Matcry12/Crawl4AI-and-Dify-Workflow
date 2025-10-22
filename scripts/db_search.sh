#!/bin/bash
# Search documents by keyword

if [ $# -eq 0 ]; then
    echo "Usage: $0 <search_term>"
    echo "Example: $0 blockchain"
    exit 1
fi

SEARCH_TERM="$1"

echo "🔍 Searching for: $SEARCH_TERM"
echo "════════════════════════════════════════════════════════════════"

docker exec docker-db-1 psql -U postgres -d crawl4ai -c "
SELECT
    d.title,
    d.mode,
    d.category,
    LEFT(d.content, 100) || '...' as preview
FROM documents d
WHERE
    d.title ILIKE '%$SEARCH_TERM%' OR
    d.content ILIKE '%$SEARCH_TERM%'
ORDER BY d.created_at DESC;
"
