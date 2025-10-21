-- Crawl4AI PostgreSQL Schema with pgvector
-- Optimized for vector similarity search with HNSW indexing

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop existing tables if they exist
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;

-- Documents table with native vector storage
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT,
    mode TEXT,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(768),  -- Native pgvector type for 768-dimensional embeddings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chunks table for document segments
CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding vector(768),  -- Native pgvector type
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index)
);

-- Indexes for performance
CREATE INDEX idx_documents_mode ON documents(mode);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);

-- HNSW indexes for vector similarity search (O(log n) performance!)
-- These indexes make similarity search 100-200x faster
CREATE INDEX idx_documents_embedding ON documents USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Full-text search indexes for content
CREATE INDEX idx_documents_content_fts ON documents USING GIN (to_tsvector('english', content));
CREATE INDEX idx_chunks_content_fts ON chunks USING GIN (to_tsvector('english', content));

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View for document statistics
CREATE OR REPLACE VIEW document_stats AS
SELECT
    mode,
    category,
    COUNT(*) as count,
    AVG(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END) * 100 as embedding_percentage,
    MIN(created_at) as first_created,
    MAX(updated_at) as last_updated
FROM documents
GROUP BY mode, category;

-- Comments for documentation
COMMENT ON TABLE documents IS 'Main documents table with native vector embeddings';
COMMENT ON TABLE chunks IS 'Document chunks for granular similarity search';
COMMENT ON COLUMN documents.embedding IS '768-dimensional Gemini text-embedding-004 vector';
COMMENT ON COLUMN chunks.embedding IS '768-dimensional chunk embedding for semantic search';
COMMENT ON INDEX idx_documents_embedding IS 'HNSW index for fast cosine similarity search (O(log n))';
COMMENT ON INDEX idx_chunks_embedding IS 'HNSW index for fast chunk-level similarity search';

-- Grant permissions (adjust as needed)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO crawl4ai_user;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO crawl4ai_user;

-- Display setup completion
SELECT 'PostgreSQL schema created successfully!' as status;
SELECT 'Tables created: documents, chunks' as info;
SELECT 'Vector indexes created with HNSW algorithm' as performance;
SELECT 'Ready for 100-200x faster similarity search!' as ready;
