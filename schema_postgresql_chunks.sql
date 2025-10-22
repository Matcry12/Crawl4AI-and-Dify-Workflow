-- ============================================================================
-- Enhanced PostgreSQL Schema for Optimized RAG with Parent-Child Chunking
-- ============================================================================
-- Database: crawl4ai
-- Extensions: pgvector
-- Strategy: 3-level hierarchy (Document → Sections → Propositions)
-- All levels embedded for hierarchical retrieval
-- ============================================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================================================
-- LEVEL 1: DOCUMENTS (with summary embeddings)
-- ============================================================================

-- This table already exists from schema_postgresql.sql
-- We'll add summary columns via ALTER TABLE

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS summary TEXT,
ADD COLUMN IF NOT EXISTS summary_embedding vector(768);

-- Index for document summary search (Level 1 filtering)
CREATE INDEX IF NOT EXISTS idx_document_summary_embedding ON documents
USING hnsw (summary_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

COMMENT ON COLUMN documents.summary IS 'Document summary (100-200 tokens) for high-level filtering';
COMMENT ON COLUMN documents.summary_embedding IS '768-dim embedding of document summary';


-- ============================================================================
-- LEVEL 2: SEMANTIC SECTIONS (Enhanced Parent Chunks)
-- ============================================================================
-- Size: 200-400 tokens (optimal for LLM attention)
-- Purpose: Topic-level retrieval
-- Embedded: YES (this is the key difference from Dify)
-- ============================================================================

CREATE TABLE IF NOT EXISTS semantic_sections (
    -- Primary key
    id                  TEXT PRIMARY KEY,

    -- Foreign key to documents
    document_id         TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_index       INT NOT NULL,

    -- Content
    header              TEXT,           -- Section header (e.g., "## Introduction to EOS")
    content             TEXT NOT NULL,  -- Full section text (200-400 tokens)
    token_count         INT NOT NULL,

    -- Embeddings (YES - sections are embedded!)
    embedding           vector(768) NOT NULL,

    -- Metadata for better retrieval
    keywords            TEXT[],         -- ["consensus", "DPoS", "validators"]
    topics              TEXT[],         -- ["blockchain", "governance"]
    section_type        TEXT,           -- "introduction", "tutorial", "reference", "example"

    -- Navigation (linked list structure)
    prev_section_id     TEXT,           -- Link to previous section in document
    next_section_id     TEXT,           -- Link to next section in document

    -- Timestamps
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure uniqueness within document
    UNIQUE(document_id, section_index)
);

-- HNSW index for fast vector similarity search on sections (CRITICAL!)
CREATE INDEX idx_section_embeddings ON semantic_sections
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Regular indexes for filtering
CREATE INDEX idx_section_document ON semantic_sections(document_id);
CREATE INDEX idx_section_type ON semantic_sections(section_type);
CREATE INDEX idx_section_keywords ON semantic_sections USING gin(keywords);
CREATE INDEX idx_section_topics ON semantic_sections USING gin(topics);

-- Comments
COMMENT ON TABLE semantic_sections IS 'Semantic sections (200-400 tokens) for topic-level retrieval';
COMMENT ON COLUMN semantic_sections.embedding IS '768-dim embedding of section content';
COMMENT ON COLUMN semantic_sections.section_type IS 'Classification: introduction, tutorial, reference, example, comparison';


-- ============================================================================
-- LEVEL 3: SEMANTIC PROPOSITIONS (Enhanced Child Chunks)
-- ============================================================================
-- Size: 50-150 tokens (complete thoughts)
-- Purpose: Fact-level retrieval
-- Embedded: YES (all propositions embedded)
-- ============================================================================

CREATE TABLE IF NOT EXISTS semantic_propositions (
    -- Primary key
    id                  TEXT PRIMARY KEY,

    -- Foreign key to sections
    section_id          TEXT NOT NULL REFERENCES semantic_sections(id) ON DELETE CASCADE,
    proposition_index   INT NOT NULL,

    -- Content
    content             TEXT NOT NULL,  -- Complete, self-contained proposition
    token_count         INT NOT NULL,

    -- Embeddings (YES - propositions are embedded!)
    embedding           vector(768) NOT NULL,

    -- Semantic metadata
    proposition_type    TEXT,           -- "definition", "procedure", "example", "comparison", "statement"
    entities            TEXT[],         -- Named entities: ["EOS Network", "DPoS", "block producers"]
    keywords            TEXT[],         -- Keywords for filtering

    -- Quality metrics (optional, can be computed)
    completeness_score  FLOAT DEFAULT 1.0,  -- How self-contained (0.0-1.0)

    -- Timestamps
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure uniqueness within section
    UNIQUE(section_id, proposition_index)
);

-- HNSW index for fast vector similarity search on propositions (CRITICAL!)
CREATE INDEX idx_proposition_embeddings ON semantic_propositions
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Regular indexes for filtering
CREATE INDEX idx_proposition_section ON semantic_propositions(section_id);
CREATE INDEX idx_proposition_type ON semantic_propositions(proposition_type);
CREATE INDEX idx_proposition_keywords ON semantic_propositions USING gin(keywords);
CREATE INDEX idx_proposition_entities ON semantic_propositions USING gin(entities);

-- Comments
COMMENT ON TABLE semantic_propositions IS 'Semantic propositions (50-150 tokens) for fact-level retrieval';
COMMENT ON COLUMN semantic_propositions.embedding IS '768-dim embedding of proposition content';
COMMENT ON COLUMN semantic_propositions.proposition_type IS 'Classification: definition, procedure, example, comparison, statement';
COMMENT ON COLUMN semantic_propositions.completeness_score IS 'Self-containment score (1.0 = fully self-contained)';


-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View: Complete document hierarchy
CREATE OR REPLACE VIEW document_hierarchy AS
SELECT
    d.id as document_id,
    d.title as document_title,
    d.category as document_category,
    d.mode as document_mode,
    d.summary as document_summary,
    s.id as section_id,
    s.header as section_header,
    s.section_index,
    s.token_count as section_tokens,
    p.id as proposition_id,
    p.content as proposition_content,
    p.proposition_index,
    p.proposition_type,
    p.token_count as proposition_tokens
FROM documents d
LEFT JOIN semantic_sections s ON d.id = s.document_id
LEFT JOIN semantic_propositions p ON s.id = p.section_id
ORDER BY d.id, s.section_index, p.proposition_index;

COMMENT ON VIEW document_hierarchy IS 'Complete 3-level document hierarchy for debugging';


-- View: Document chunk statistics
CREATE OR REPLACE VIEW document_chunk_stats AS
SELECT
    d.id,
    d.title,
    d.category,
    d.mode,
    COUNT(DISTINCT s.id) as section_count,
    COUNT(DISTINCT p.id) as proposition_count,
    SUM(s.token_count) as total_section_tokens,
    AVG(s.token_count) as avg_section_tokens,
    AVG(p.token_count) as avg_proposition_tokens,
    CASE
        WHEN d.summary_embedding IS NOT NULL THEN true
        ELSE false
    END as has_summary_embedding,
    CASE
        WHEN COUNT(DISTINCT s.id) > 0 THEN true
        ELSE false
    END as has_sections,
    CASE
        WHEN COUNT(DISTINCT p.id) > 0 THEN true
        ELSE false
    END as has_propositions
FROM documents d
LEFT JOIN semantic_sections s ON d.id = s.document_id
LEFT JOIN semantic_propositions p ON s.id = p.section_id
GROUP BY d.id, d.title, d.category, d.mode, d.summary_embedding;

COMMENT ON VIEW document_chunk_stats IS 'Statistics about document chunking and embedding coverage';


-- View: Section with proposition count
CREATE OR REPLACE VIEW section_summary AS
SELECT
    s.id,
    s.document_id,
    s.header,
    s.section_index,
    s.token_count,
    s.section_type,
    COUNT(p.id) as proposition_count,
    SUM(p.token_count) as total_proposition_tokens,
    ARRAY_AGG(p.proposition_type) FILTER (WHERE p.proposition_type IS NOT NULL) as proposition_types
FROM semantic_sections s
LEFT JOIN semantic_propositions p ON s.id = p.section_id
GROUP BY s.id, s.document_id, s.header, s.section_index, s.token_count, s.section_type
ORDER BY s.document_id, s.section_index;

COMMENT ON VIEW section_summary IS 'Section statistics with proposition counts';


-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Function: Get document hierarchy as JSON
CREATE OR REPLACE FUNCTION get_document_chunks(doc_id TEXT)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'document', json_build_object(
            'id', d.id,
            'title', d.title,
            'summary', d.summary
        ),
        'sections', (
            SELECT json_agg(
                json_build_object(
                    'id', s.id,
                    'header', s.header,
                    'index', s.section_index,
                    'token_count', s.token_count,
                    'propositions', (
                        SELECT json_agg(
                            json_build_object(
                                'id', p.id,
                                'content', p.content,
                                'type', p.proposition_type,
                                'index', p.proposition_index
                            )
                            ORDER BY p.proposition_index
                        )
                        FROM semantic_propositions p
                        WHERE p.section_id = s.id
                    )
                )
                ORDER BY s.section_index
            )
            FROM semantic_sections s
            WHERE s.document_id = d.id
        )
    ) INTO result
    FROM documents d
    WHERE d.id = doc_id;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_document_chunks IS 'Get complete document hierarchy as nested JSON';


-- Function: Search sections by similarity
CREATE OR REPLACE FUNCTION search_sections_by_similarity(
    query_embedding vector(768),
    top_k INT DEFAULT 10,
    min_score FLOAT DEFAULT 0.0
)
RETURNS TABLE(
    section_id TEXT,
    document_id TEXT,
    document_title TEXT,
    section_header TEXT,
    content TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.id,
        s.document_id,
        d.title,
        s.header,
        s.content,
        1 - (s.embedding <=> query_embedding) as similarity
    FROM semantic_sections s
    JOIN documents d ON s.document_id = d.id
    WHERE s.embedding IS NOT NULL
    AND 1 - (s.embedding <=> query_embedding) >= min_score
    ORDER BY s.embedding <=> query_embedding
    LIMIT top_k;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_sections_by_similarity IS 'Search sections by vector similarity';


-- Function: Search propositions by similarity
CREATE OR REPLACE FUNCTION search_propositions_by_similarity(
    query_embedding vector(768),
    top_k INT DEFAULT 20,
    min_score FLOAT DEFAULT 0.0
)
RETURNS TABLE(
    proposition_id TEXT,
    section_id TEXT,
    content TEXT,
    proposition_type TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.section_id,
        p.content,
        p.proposition_type,
        1 - (p.embedding <=> query_embedding) as similarity
    FROM semantic_propositions p
    WHERE p.embedding IS NOT NULL
    AND 1 - (p.embedding <=> query_embedding) >= min_score
    ORDER BY p.embedding <=> query_embedding
    LIMIT top_k;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_propositions_by_similarity IS 'Search propositions by vector similarity';


-- ============================================================================
-- INDEXES SUMMARY
-- ============================================================================

-- Document level:
--   idx_documents_embedding (existing, for content)
--   idx_document_summary_embedding (new, for summaries)

-- Section level:
--   idx_section_embeddings (HNSW, for vector search)
--   idx_section_document (for filtering by document)
--   idx_section_type (for filtering by type)
--   idx_section_keywords (GIN, for keyword search)
--   idx_section_topics (GIN, for topic search)

-- Proposition level:
--   idx_proposition_embeddings (HNSW, for vector search)
--   idx_proposition_section (for filtering by section)
--   idx_proposition_type (for filtering by type)
--   idx_proposition_keywords (GIN, for keyword search)
--   idx_proposition_entities (GIN, for entity search)


-- ============================================================================
-- MIGRATION FROM OLD SCHEMA
-- ============================================================================

-- If you already have documents in the old schema, you can migrate them
-- by running the chunking process on existing content.
-- This will be handled by the migration script.


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check extension
-- SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check tables
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%section%' OR table_name LIKE '%proposition%';

-- Check indexes
-- SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename IN ('semantic_sections', 'semantic_propositions');

-- Check document stats
-- SELECT * FROM document_chunk_stats ORDER BY id;

-- Test search function
-- SELECT * FROM search_sections_by_similarity('[0.1,0.2,...]'::vector, 5, 0.7);
