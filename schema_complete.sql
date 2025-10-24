-- ============================================================================
-- Complete PostgreSQL Schema for Crawl4AI RAG System with pgvector
-- ============================================================================
-- Database: crawl4ai
-- Extensions: pgvector
-- Strategy: 3-level hierarchy (Document → Sections → Propositions)
-- ============================================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- BASE TABLES
-- ============================================================================

-- Documents table (base level)
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT,
    mode TEXT NOT NULL,  -- 'paragraph' or 'full-doc'
    summary TEXT,  -- Document summary for embeddings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_mode ON documents(mode);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);

-- Embeddings table (unified storage for all entity types)
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,  -- 'document_summary', 'section', 'proposition'
    entity_id TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_entity ON embeddings(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
ON embeddings USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- LEVEL 2: SEMANTIC SECTIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS semantic_sections (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_index INT NOT NULL,
    header TEXT,
    content TEXT NOT NULL,
    token_count INT NOT NULL,
    embedding vector(768),
    keywords TEXT[],
    topics TEXT[],
    section_type TEXT,
    prev_section_id TEXT,
    next_section_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, section_index)
);

CREATE INDEX IF NOT EXISTS idx_section_embeddings
ON semantic_sections USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_section_document ON semantic_sections(document_id);
CREATE INDEX IF NOT EXISTS idx_section_type ON semantic_sections(section_type);
CREATE INDEX IF NOT EXISTS idx_section_keywords ON semantic_sections USING gin(keywords);
CREATE INDEX IF NOT EXISTS idx_section_topics ON semantic_sections USING gin(topics);

-- ============================================================================
-- LEVEL 3: SEMANTIC PROPOSITIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS semantic_propositions (
    id TEXT PRIMARY KEY,
    section_id TEXT NOT NULL REFERENCES semantic_sections(id) ON DELETE CASCADE,
    proposition_index INT NOT NULL,
    content TEXT NOT NULL,
    token_count INT NOT NULL,
    embedding vector(768),
    proposition_type TEXT,
    entities TEXT[],
    keywords TEXT[],
    completeness_score FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(section_id, proposition_index)
);

CREATE INDEX IF NOT EXISTS idx_proposition_embeddings
ON semantic_propositions USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_proposition_section ON semantic_propositions(section_id);
CREATE INDEX IF NOT EXISTS idx_proposition_type ON semantic_propositions(proposition_type);
CREATE INDEX IF NOT EXISTS idx_proposition_keywords ON semantic_propositions USING gin(keywords);
CREATE INDEX IF NOT EXISTS idx_proposition_entities ON semantic_propositions USING gin(entities);

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

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

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION search_similar_documents(
    query_embedding vector(768),
    mode_filter TEXT DEFAULT NULL,
    top_k INT DEFAULT 10,
    min_score FLOAT DEFAULT 0.0
)
RETURNS TABLE(
    document_id TEXT,
    title TEXT,
    mode TEXT,
    category TEXT,
    summary TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.title,
        d.mode,
        d.category,
        d.summary,
        1 - (e.embedding <=> query_embedding) as similarity
    FROM documents d
    JOIN embeddings e ON e.entity_type = 'document_summary' AND e.entity_id = d.id
    WHERE (mode_filter IS NULL OR d.mode = mode_filter)
      AND 1 - (e.embedding <=> query_embedding) >= min_score
    ORDER BY e.embedding <=> query_embedding
    LIMIT top_k;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION search_similar_sections(
    query_embedding vector(768),
    mode_filter TEXT DEFAULT NULL,
    top_k INT DEFAULT 5,
    min_score FLOAT DEFAULT 0.5
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
      AND (mode_filter IS NULL OR d.mode = mode_filter)
      AND 1 - (s.embedding <=> query_embedding) >= min_score
    ORDER BY s.embedding <=> query_embedding
    LIMIT top_k;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Verification
-- ============================================================================

SELECT 'Schema created successfully!' as status;
SELECT 'Checking pgvector extension:' as info;
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
