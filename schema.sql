-- ============================================================================
-- Topic-Based Document Management Database Schema
-- ============================================================================
-- Description: PostgreSQL + pgvector schema for topic-based document storage
--              with triple-layer filtering (SQL + Embedding + LLM)
-- Date: 2025-10-10
-- ============================================================================

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS document_sources CASCADE;
DROP TABLE IF EXISTS documents CASCADE;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;        -- Vector similarity search
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- Fuzzy text matching
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- UUID generation

-- ============================================================================
-- MAIN TABLES
-- ============================================================================

-- Documents table with rich metadata for triple-layer filtering
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core content
    topic_title VARCHAR(500) NOT NULL,
    topic_summary TEXT,
    content TEXT NOT NULL,
    embedding vector(768),  -- Gemini text-embedding-004 embeddings (768 dimensions)

    -- Metadata for SQL Layer 1 filtering
    category VARCHAR(100),              -- 'wallet_management', 'security', 'trading', etc.
    keywords TEXT[],                    -- ['wallet', 'account', 'creation']
    source_domain VARCHAR(255),         -- 'docs.example.com'
    content_type VARCHAR(50),           -- 'tutorial', 'reference', 'api_docs', 'troubleshooting'
    mode VARCHAR(20),                   -- 'full_doc' or 'paragraph' (dual-mode strategy)

    -- Statistics
    word_count INT DEFAULT 0,
    version_count INT DEFAULT 1,
    popularity_score FLOAT DEFAULT 0.0,  -- Track usage for relevance ranking

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Full-text search vector (automatically maintained)
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', topic_title), 'A') ||
        setweight(to_tsvector('english', coalesce(topic_summary, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(category, '')), 'C')
    ) STORED,

    -- Constraints
    CHECK (word_count >= 0),
    CHECK (version_count >= 1),
    CHECK (popularity_score >= 0.0)
);

-- Source tracking table (many pages can contribute to one topic)
CREATE TABLE document_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    source_url TEXT NOT NULL,
    contributed_at TIMESTAMP DEFAULT NOW(),
    content_delta TEXT,  -- Preview/summary of what was added from this source

    -- Constraints
    CONSTRAINT unique_source_per_doc UNIQUE(document_id, source_url)
);

-- ============================================================================
-- INDEXES FOR TRIPLE-LAYER FILTERING
-- ============================================================================

-- Layer 1: SQL Filtering Indexes (eliminate 70-80% of documents)
CREATE INDEX idx_documents_search ON documents USING GIN(search_vector);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_keywords ON documents USING GIN(keywords);
CREATE INDEX idx_documents_updated ON documents(updated_at DESC);
CREATE INDEX idx_documents_domain ON documents(source_domain);
CREATE INDEX idx_documents_content_type ON documents(content_type);
CREATE INDEX idx_documents_mode ON documents(mode);

-- Combined indexes for common filter combinations
CREATE INDEX idx_documents_cat_updated ON documents(category, updated_at DESC);
CREATE INDEX idx_documents_cat_type ON documents(category, content_type);

-- Layer 2: Vector Search Index (eliminate 99%+ of remaining documents)
-- Note: Adjust 'lists' parameter based on dataset size
--   - lists = sqrt(total_documents) is a good starting point
--   - For 10K docs: lists = 100
--   - For 100K docs: lists = 316
--   - For 1M docs: lists = 1000
CREATE INDEX idx_documents_embedding ON documents
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Source tracking indexes
CREATE INDEX idx_sources_url ON document_sources(source_url);
CREATE INDEX idx_sources_doc_id ON document_sources(document_id);
CREATE INDEX idx_sources_contributed ON document_sources(contributed_at DESC);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at on document changes
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- EXAMPLE QUERIES FOR TRIPLE-LAYER FILTERING
-- ============================================================================

-- Example 1: Full triple-layer query (SQL + Vector filtering combined)
-- Layer 3 (LLM) happens in application code
COMMENT ON TABLE documents IS
'Example Query:
SELECT
    id, topic_title, topic_summary, category, keywords, embedding, word_count,
    1 - (embedding <=> $1::vector) as similarity
FROM documents
WHERE
    -- Layer 1: SQL Filters (metadata-based)
    category = $2
    AND keywords && $3::text[]
    AND search_vector @@ to_tsquery(''english'', $4)
    -- Layer 2: Vector Similarity
    AND 1 - (embedding <=> $1::vector) > $5
ORDER BY embedding <=> $1::vector
LIMIT 5;

Parameters:
$1: query_embedding (vector)
$2: category (text)
$3: keywords (text[])
$4: search_terms (tsquery)
$5: similarity_threshold (float, typically 0.75)
';

-- ============================================================================
-- SAMPLE DATA FOR TESTING
-- ============================================================================

-- Insert sample document for testing
INSERT INTO documents (
    topic_title,
    topic_summary,
    content,
    embedding,
    category,
    keywords,
    source_domain,
    content_type,
    word_count
) VALUES (
    'Complete Wallet Account Creation Guide',
    'Step-by-step guide to creating a cryptocurrency wallet account including costs, requirements, and verification steps.',
    'This comprehensive guide covers everything you need to know about creating a wallet account...',
    array_fill(0.1, ARRAY[768])::vector,  -- Placeholder embedding
    'wallet_management',
    ARRAY['wallet', 'account', 'creation', 'setup', 'guide'],
    'docs.example.com',
    'tutorial',
    1500
);

-- Get the document ID for source tracking
WITH doc AS (
    SELECT id FROM documents WHERE topic_title = 'Complete Wallet Account Creation Guide'
)
INSERT INTO document_sources (document_id, source_url, content_delta)
SELECT id, 'https://docs.example.com/wallet-setup', 'Original content'
FROM doc;

-- ============================================================================
-- STATISTICS AND MONITORING
-- ============================================================================

-- View to get database statistics
CREATE OR REPLACE VIEW database_stats AS
SELECT
    COUNT(*) as total_documents,
    COUNT(DISTINCT category) as total_categories,
    SUM(word_count) as total_words,
    AVG(word_count) as avg_words_per_doc,
    AVG(version_count) as avg_versions,
    MAX(updated_at) as last_update,
    MIN(created_at) as first_document
FROM documents;

-- View to get category breakdown
CREATE OR REPLACE VIEW category_stats AS
SELECT
    category,
    COUNT(*) as doc_count,
    AVG(word_count) as avg_words,
    SUM(word_count) as total_words,
    MAX(updated_at) as last_updated
FROM documents
WHERE category IS NOT NULL
GROUP BY category
ORDER BY doc_count DESC;

-- View to get most contributed sources
CREATE OR REPLACE VIEW top_sources AS
SELECT
    source_url,
    COUNT(DISTINCT document_id) as documents_contributed,
    MAX(contributed_at) as last_contribution
FROM document_sources
GROUP BY source_url
ORDER BY documents_contributed DESC
LIMIT 20;

-- ============================================================================
-- GRANTS (adjust based on your user setup)
-- ============================================================================

-- Grant permissions to application user (replace 'crawl4ai_user' with your username)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO crawl4ai_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO crawl4ai_user;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check extensions are installed
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'pg_trgm', 'uuid-ossp');

-- Check tables exist
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- Check indexes exist
SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname;

-- Verify sample data
SELECT COUNT(*) as sample_documents FROM documents;
SELECT COUNT(*) as sample_sources FROM document_sources;

-- Test vector similarity query (using sample data)
SELECT
    id,
    topic_title,
    1 - (embedding <=> array_fill(0.1, ARRAY[768])::vector) as similarity
FROM documents
ORDER BY embedding <=> array_fill(0.1, ARRAY[768])::vector
LIMIT 5;

COMMENT ON SCHEMA public IS 'Topic-Based Document Management Schema - Ready for use!';
