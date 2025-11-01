#!/bin/bash
# Watch database changes in real-time (updates every 2 seconds)
# Press Ctrl+C to stop

watch -n 2 'docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -t -c "
SELECT
    '\''📊 Database Status'\'' as title,
    '\''────────────────────────'\'' as separator
UNION ALL
SELECT
    '\''Documents:     '\'' || COUNT(*)::text,
    '\'''\''
FROM documents
UNION ALL
SELECT
    '\''Sections:      '\'' || COUNT(*)::text,
    '\'''\''
FROM semantic_sections
UNION ALL
SELECT
    '\''Propositions:  '\'' || COUNT(*)::text,
    '\'''\''
FROM semantic_propositions
UNION ALL
SELECT
    '\''Embeddings:    '\'' || COUNT(*)::text,
    '\'''\''
FROM embeddings
UNION ALL
SELECT
    '\'''\'' as blank,
    '\'''\''
UNION ALL
SELECT
    '\''📄 Latest Documents'\'' as title,
    '\''────────────────────────'\''
UNION ALL
SELECT
    title || '\'' (('\'' || mode || '\'')'\'' as doc,
    to_char(created_at, '\''HH24:MI:SS'\'') as time
FROM documents
ORDER BY created_at DESC
LIMIT 5;
"'
