#!/bin/bash
# Add mode column to existing database

CONTAINER="docker-db-1"

echo "========================================================================"
echo "🔄 Adding 'mode' Column for Dual-Mode Strategy"
echo "========================================================================"
echo ""

echo "Adding mode column to documents table..."
docker exec $CONTAINER psql -U postgres -d crawl4ai -c "
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS mode VARCHAR(20);
" 2>&1

echo "Creating index on mode column..."
docker exec $CONTAINER psql -U postgres -d crawl4ai -c "
    CREATE INDEX IF NOT EXISTS idx_documents_mode ON documents(mode);
" 2>&1

echo ""
echo "✅ Mode column added successfully!"
echo ""
echo "Note: Existing documents have mode=NULL."
echo "They will work fine, but new documents will have mode='full_doc' or 'paragraph'."
echo ""
