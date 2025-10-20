#!/bin/bash
# Project Cleanup Script
# Removes obsolete files from old workflows and experiments

echo "🧹 Crawl4AI Project Cleanup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This will remove:"
echo "  • ~28 obsolete documentation files"
echo "  • ~30 old test files"
echo "  • ~10 migration scripts (already executed)"
echo "  • ~8 unused folders"
echo "  • Old test databases"
echo ""
read -p "Continue with cleanup? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "❌ Cleanup cancelled"
    exit 1
fi

echo ""
echo "🗑️  Removing old documentation files..."

# Old documentation from previous iterations
rm -f ARCHITECTURE_AND_IMPROVEMENTS.md
rm -f BFS_CRAWLER_GUIDE.md
rm -f CLEAN_STRUCTURE.md
rm -f COMPLETE_EXTRACTION_GUIDE.md
rm -f COMPLETE_FLOW_DIAGRAM.md
rm -f DATABASE_SETUP.md
rm -f DATABASE_TEST_COMPLETE.md
rm -f DOCUMENTATION_INDEX.md
rm -f DUAL_MODE_IMPLEMENTATION.md
rm -f DUAL_MODE_STRATEGY.md
rm -f EXPERT_ANALYSIS.md
rm -f FINAL_STATUS.md
rm -f FINAL_TEST_ANALYSIS.md
rm -f FLOW_DIAGRAM.md
rm -f FORMATTER_MODE_EXAMPLES.md
rm -f GEMINI_EMBEDDINGS_MIGRATION.md
rm -f HOW_TO_TEST_EXTRACTOR.md
rm -f HYBRID_CHUNKING_README.md
rm -f IMPLEMENTATION_PLAN.md
rm -f IMPLEMENTATION_STATUS.md
rm -f INTERACTIVE_TEST_README.md
rm -f NATURAL_FORMATTER_COMPLETE.md
rm -f NATURAL_FORMATTER_PLAN.md
rm -f OMNITROVE_QUALITY_REPORT.md
rm -f OMNITROVE_QUALITY_REPORT_IMPROVED.md
rm -f PHASE1_IMPLEMENTATION_COMPLETE.md
rm -f PROJECT_STATUS.md
rm -f PROJECT_STATUS_UPDATE.md
rm -f PROJECT_STRUCTURE.md
rm -f QUICK_START.md
rm -f README_DATABASE.md
rm -f SEPARATOR_METHODS_ANALYSIS.md
rm -f SESSION_SUMMARY.md
rm -f SMART_CHUNKING_SUMMARY.md
rm -f SMART_STRATEGY_ARCHITECTURE.md
rm -f STATUS_SUMMARY.md
rm -f TEST_FILES_STATUS.md
rm -f TESTING_GUIDE.md
rm -f TODO.md
rm -f TOPIC_BASED_ARCHITECTURE.md
rm -f TOPIC_EXTRACTOR_COMPLETE.md
rm -f TOPIC_STRUCTURE.md
rm -f TUTORIAL_SUMMARY.md
rm -f UNIFIED_PIPELINE_GUIDE.md
rm -f UPDATE_SUMMARY.md
rm -f WHAT_YOU_CAN_DO.md
rm -f WORKFLOW_GUIDE.md

echo "✅ Documentation files removed"

echo ""
echo "🗑️  Removing old test files..."

# Old test scripts and results
rm -f demo_formatter_examples.py
rm -f example_unified_pipeline.py
rm -f test_chunk_based_matching.py
rm -f test_chunk_based_results.json
rm -f test_chunk_with_rewriting.py
rm -f test_database.py
rm -f test_delimiter_structure.py
rm -f test_document_merger.py
rm -f test_dual_mode.py
rm -f test_embedding_search.py
rm -f test_expansion_prompt.py
rm -f test_gemini_embeddings.py
rm -f test_matching_comprehensive.py
rm -f test_matching_improved.py
rm -f test_matching_with_llm.py
rm -f test_my_content.py
rm -f test_natural_formatter_manual.py
rm -f test_omnitrove_extraction.py
rm -f test_rag_database.py
rm -f test_rag_db_simple.py
rm -f test_rag_merge.py
rm -f test_rag_simple.py
rm -f test_search_queries.py
rm -f test_search.py
rm -f test_simple_example.py
rm -f test_smart_strategy.py
rm -f test_smart_strategy_fast.py
rm -f test_topic_extractor_manual.py
rm -f test_topic_similarity.py
rm -f test_data_insert.sql
rm -f test_content_omnitrove.md
rm -f test_extracted_topics_manual.json
rm -f test_rewriting_comparison.json

echo "✅ Test files removed"

echo ""
echo "🗑️  Removing test databases and folders..."

# Test data folders and databases
rm -rf test_documents/
rm -f test_documents.db
rm -rf test_merged_documents/
rm -f test_workflow.db
rm -rf test_workflow_docs/
rm -rf test_workflow_merged/

echo "✅ Test data removed"

echo ""
echo "🗑️  Removing old migration scripts..."

# One-time migration scripts (already executed)
rm -f migrate_to_gemini.sh
rm -f quick_migrate.sh
rm -f fix_embeddings.sh
rm -f add_mode_column.sh
rm -f generate_embeddings.py
rm -f generate_embeddings_docker.py
rm -f update_embeddings_docker.py
rm -f run_embedding_test_docker.sh
rm -f test_docker_database.sh
rm -f setup_database.sh
rm -f schema.sql
rm -f test.sh

echo "✅ Migration scripts removed"

echo ""
echo "🗑️  Removing old pipeline files..."

# Old architecture files
rm -f unified_pipeline.py
rm -f build_kb.py
rm -f interactive_search_test.py
rm -f main.py

echo "✅ Old pipeline files removed"

echo ""
echo "🗑️  Removing cache and checkpoint files..."

# Checkpoint and cache files
rm -f crawl_checkpoint.json
rm -f omnitrove_extracted_topics.json

echo "✅ Cache files removed"

echo ""
echo "🗑️  Removing unused folders..."

# Unused folders from old architecture
rm -rf backup_old/
rm -rf crawled_content/
rm -rf core/
rm -rf examples/
rm -rf models/
rm -rf output/
rm -rf prompts/
rm -rf tests/

echo "✅ Unused folders removed"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Cleanup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Summary:"
echo "  ✅ Removed ~28 documentation files"
echo "  ✅ Removed ~30 test files"
echo "  ✅ Removed ~10 migration scripts"
echo "  ✅ Removed ~8 unused folders"
echo "  ✅ Removed test databases"
echo ""
echo "💾 Estimated space saved: 2-3 MB"
echo ""
echo "🎯 Project Structure (After Cleanup):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📁 Core Workflow Files:"
echo "    • bfs_crawler.py           - Web crawler"
echo "    • extract_topics.py        - Topic extraction"
echo "    • embedding_search.py      - Similarity search"
echo "    • document_creator.py      - Document generation"
echo "    • document_merger.py       - Document merging"
echo "    • document_database.py     - Vector database"
echo "    • workflow_manager.py      - Workflow orchestration"
echo ""
echo "  📁 Active Data:"
echo "    • bfs_crawled/             - Crawl results"
echo "    • documents/               - Generated documents"
echo "    • documents.db             - Vector database"
echo ""
echo "  📁 Configuration:"
echo "    • .env                     - Environment variables"
echo "    • .env.example             - Configuration template"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Your project is now clean and focused!"
echo ""
