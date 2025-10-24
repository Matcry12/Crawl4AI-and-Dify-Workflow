#!/bin/bash
# Cleanup script for preparing repository for git
# Run this before committing to remove temporary and generated files

set -e  # Exit on error

echo "=================================================="
echo "🧹 Crawl4AI Repository Cleanup"
echo "=================================================="
echo ""

# Navigate to repository root
cd "$(dirname "$0")"

echo "📋 Cleanup Plan:"
echo ""
echo "Will remove:"
echo "  - Temporary crawled data (bfs_crawled/)"
echo "  - Generated merged documents (merged_documents/)"
echo "  - Test scripts (test_*.py)"
echo "  - Temporary SQL files"
echo "  - Session notes and outdated docs"
echo ""
echo "Will keep:"
echo "  - Core source code"
echo "  - Important documentation"
echo "  - Configuration examples"
echo ""

read -p "Continue with cleanup? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cleanup cancelled"
    exit 1
fi

echo ""
echo "🗑️  Starting cleanup..."
echo ""

# Category 1: Remove crawled data
echo "1️⃣  Removing crawled data..."
if [ -d "bfs_crawled" ]; then
    rm -rf bfs_crawled/
    echo "   ✅ Removed bfs_crawled/"
fi

# Category 2: Remove merged documents
echo "2️⃣  Removing merged documents..."
if [ -d "merged_documents" ]; then
    rm -rf merged_documents/
    echo "   ✅ Removed merged_documents/"
fi

# Category 3: Remove test files
echo "3️⃣  Removing test files..."
rm -f test_dify_api.py
rm -f test_embedding_optimization.py
rm -f test_embedding_retrieval.py
rm -f test_postgres_vector_search.py
rm -f test_vector_storage.py
echo "   ✅ Removed test_*.py files"

# Category 4: Remove temporary SQL and scripts
echo "4️⃣  Removing temporary SQL/scripts..."
rm -f migrate_embeddings_to_vector.sql
rm -f fix_dify_connection.sh
rm -f search_documents.py
echo "   ✅ Removed temporary SQL and script files"

# Category 5: Remove session notes and redundant docs
echo "5️⃣  Removing session notes..."
rm -f ACADEMIC_ANALYSIS_AND_IMPROVEMENTS.md
rm -f ACADEMIC_RE_EVALUATION.md
rm -f SESSION_SUMMARY_2025-10-23.md
rm -f IMPROVEMENT_ROADMAP.md
echo "   ✅ Removed session note files"

# Category 6: Create output directories (with .gitkeep)
echo "6️⃣  Creating output directories with .gitkeep..."
mkdir -p bfs_crawled
echo "# Crawled data will be stored here" > bfs_crawled/.gitkeep
mkdir -p merged_documents
echo "# Merged documents will be stored here" > merged_documents/.gitkeep
echo "   ✅ Created output directories"

echo ""
echo "=================================================="
echo "✅ Cleanup complete!"
echo "=================================================="
echo ""
echo "Summary:"
echo "  - Removed temporary data and test files"
echo "  - Created output directories with .gitkeep"
echo "  - Repository is ready for git commit"
echo ""
echo "Next steps:"
echo "  1. Review changes: git status"
echo "  2. Add changes: git add ."
echo "  3. Commit: git commit -m 'Clean up repository and remove temporary files'"
echo ""
