#!/usr/bin/env python3
"""
Dify External Knowledge API Wrapper - Simplified Version
Provides a REST API endpoint compatible with Dify.ai's External Knowledge API specification.

Updated to work with simplified 3-table schema (documents, chunks, merge_history).
Uses Parent Document Retrieval: searches chunks, returns full documents.
"""

import os
import sys
from flask import Flask, request, jsonify
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chunked_document_database import ChunkedDocumentDatabase
from embedding_search import EmbeddingSearcher

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv('DIFY_API_KEY', 'your-secret-api-key-here')
KNOWLEDGE_ID = os.getenv('KNOWLEDGE_ID', 'crawl4ai-rag-kb')
RETURN_MODE = os.getenv('RETURN_MODE', 'document')  # document or chunk
PORT = int(os.getenv('DIFY_API_PORT', 5000))

# Initialize Flask app
app = Flask(__name__)

# Initialize RAG system
db = ChunkedDocumentDatabase()
searcher = EmbeddingSearcher(
    api_key=os.getenv('GEMINI_API_KEY'),
    use_postgres_search=True,
    db=db
)

print("=" * 80)
print("🚀 Dify External Knowledge API Server - Simplified Version")
print("=" * 80)
print(f"Knowledge ID: {KNOWLEDGE_ID}")
print(f"Return Mode: {RETURN_MODE} (document: full docs, chunk: individual chunks)")
print(f"Port: {PORT}")
print(f"API Key configured: {'✅' if API_KEY and API_KEY != 'your-secret-api-key-here' else '❌'}")
print(f"Database: PostgreSQL with pgvector (Parent Document Retrieval)")
print("=" * 80)
print()


def verify_api_key(auth_header: Optional[str]) -> tuple[bool, Optional[str], int]:
    """
    Verify the API key from Authorization header.

    Returns:
        (is_valid, error_message, error_code)
    """
    if not auth_header:
        return False, "Missing Authorization header", 1001

    # Expected format: "Bearer <api-key>"
    parts = auth_header.split(' ')
    if len(parts) != 2 or parts[0] != 'Bearer':
        return False, "Invalid Authorization header format. Expected 'Bearer <api-key>'", 1001

    api_key = parts[1]
    if api_key != API_KEY:
        return False, "Invalid API key", 1002

    return True, None, None


def search_knowledge(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.0,
    return_mode: str = None
) -> List[Dict]:
    """
    Search the knowledge base using Parent Document Retrieval.

    Searches chunks for precision, returns full documents for completeness.

    Args:
        query: User's question
        top_k: Number of results to return
        score_threshold: Minimum similarity score (0-1)
        return_mode: What to return - 'document' (full docs) or 'chunk' (individual chunks)

    Returns:
        List of records with content, score, title, and metadata
    """
    # Use configured default if not specified
    if not return_mode:
        return_mode = RETURN_MODE

    # Generate embedding for query
    query_embedding = searcher.create_embedding(query)
    if not query_embedding:
        return []

    # Search using Parent Document Retrieval
    # This searches chunks but returns full parent documents
    results = db.search_parent_documents(
        query_embedding=query_embedding,
        top_k=top_k,
        similarity_threshold=score_threshold
    )

    # Convert to Dify format
    records = []

    if return_mode == "chunk":
        # Return individual chunks from matching documents
        for result in results:
            doc_id = result.get('id', '')
            doc_title = result.get('title', 'Untitled')
            keywords = result.get('keywords', [])
            source_urls = result.get('source_urls', [])
            doc_score = result.get('score', 0.0)
            matching_chunks = result.get('matching_chunks', 0)

            # Return each chunk as a separate record
            for i, chunk in enumerate(result.get('chunks', [])):
                metadata = {
                    "document_id": doc_id,
                    "document_title": doc_title,
                    "chunk_id": chunk.get('id', ''),
                    "chunk_index": chunk.get('chunk_index', 0),
                    "chunk_token_count": chunk.get('token_count', 0),
                    "keywords": keywords,
                    "source_urls": source_urls,
                    "matching_chunks_in_doc": matching_chunks,
                    "return_type": "chunk"
                }

                records.append({
                    "content": chunk.get('content', ''),
                    "score": doc_score,  # Document-level score
                    "title": f"{doc_title} - Chunk {chunk.get('chunk_index', 0) + 1}",
                    "metadata": metadata
                })

    else:  # return_mode == "document"
        # Return full documents (default for Parent Document Retrieval)
        # Strategy: Search chunks for precision, return full documents for context
        for result in results:
            metadata = {
                "document_id": result.get('id', ''),
                "keywords": result.get('keywords', []),
                "source_urls": result.get('source_urls', []),
                "num_chunks": len(result.get('chunks', [])),
                "matching_chunks": result.get('matching_chunks', 0),
                "return_type": "document"
            }

            # Return FULL document content (not just summary) for LLM context
            # This is the essence of Parent Document Retrieval:
            # - Search small chunks for precision
            # - Return full documents for complete context
            content = result.get('content', '') or result.get('summary', '')

            records.append({
                "content": content,
                "score": result.get('score', 0.0),
                "title": result.get('title', 'Untitled'),
                "metadata": metadata
            })

    return records


@app.route('/retrieval', methods=['POST'])
def retrieval():
    """
    Dify External Knowledge API endpoint.

    Accepts POST requests with query and retrieval settings,
    returns relevant knowledge base records.
    """
    # Verify authentication
    auth_header = request.headers.get('Authorization')
    is_valid, error_msg, error_code = verify_api_key(auth_header)

    if not is_valid:
        return jsonify({
            "error_code": error_code,
            "error_msg": error_msg
        }), 403

    # Parse request
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify({
            "error_code": 1003,
            "error_msg": f"Invalid JSON: {str(e)}"
        }), 400

    # Validate required fields
    knowledge_id = data.get('knowledge_id')
    query = data.get('query')
    retrieval_setting = data.get('retrieval_setting', {})

    if not knowledge_id:
        return jsonify({
            "error_code": 1004,
            "error_msg": "Missing required field: knowledge_id"
        }), 400

    if knowledge_id != KNOWLEDGE_ID:
        return jsonify({
            "error_code": 2001,
            "error_msg": f"Knowledge base '{knowledge_id}' doesn't exist"
        }), 404

    if not query:
        return jsonify({
            "error_code": 1005,
            "error_msg": "Missing required field: query"
        }), 400

    # Extract retrieval settings
    top_k = retrieval_setting.get('top_k', 5)
    score_threshold = retrieval_setting.get('score_threshold', 0.0)

    # Optional: Extract custom settings (non-standard Dify fields)
    return_mode = data.get('return_mode', RETURN_MODE)  # document or chunk

    # Search knowledge base
    try:
        records = search_knowledge(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            return_mode=return_mode
        )

        print(f"📝 Query: {query[:50]}...")
        print(f"   Mode: {return_mode}")
        print(f"   Found {len(records)} results (top_k={top_k}, threshold={score_threshold})")
        if records:
            print(f"   Top score: {records[0]['score']:.4f}")
        print()

        return jsonify({
            "records": records
        }), 200

    except Exception as e:
        print(f"❌ Error during search: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            "error_code": 500,
            "error_msg": f"Internal server error: {str(e)}"
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "knowledge_id": KNOWLEDGE_ID,
        "return_mode": RETURN_MODE,
        "retrieval_strategy": "Parent Document Retrieval"
    }), 200


@app.route('/info', methods=['GET'])
def info():
    """API information endpoint."""
    # Check if API key is in header for protected info
    auth_header = request.headers.get('Authorization')
    is_valid, _, _ = verify_api_key(auth_header)

    # Count available data
    try:
        doc_count = len(db.get_all_documents_with_embeddings())
        stats = db.get_stats()
        chunk_count = stats.get('total_chunks', 0)
    except:
        doc_count = "unknown"
        chunk_count = "unknown"

    info_data = {
        "api_version": "2.0.0",  # Updated version
        "knowledge_id": KNOWLEDGE_ID,
        "default_return_mode": RETURN_MODE,
        "supported_return_modes": ["document", "chunk"],
        "retrieval_strategy": "Parent Document Retrieval (search chunks, return docs)",
        "schema": "Simplified 3-table (documents, chunks, merge_history)",
        "endpoint": "/retrieval"
    }

    # Add detailed stats only if authenticated
    if is_valid:
        info_data["documents"] = doc_count
        info_data["chunks"] = chunk_count
        info_data["database"] = "PostgreSQL with pgvector"
        info_data["index_type"] = "HNSW (ivfflat for chunks)"
        info_data["embedding_model"] = "text-embedding-004 (768-dim)"

    return jsonify(info_data), 200


if __name__ == '__main__':
    # Check if API key is set
    if API_KEY == 'your-secret-api-key-here':
        print("⚠️  WARNING: Using default API key!")
        print("   Set DIFY_API_KEY in .env file for production use")
        print()

    # Run Flask app
    print(f"🚀 Starting server on http://0.0.0.0:{PORT}")
    print(f"   Health check: http://localhost:{PORT}/health")
    print(f"   API info: http://localhost:{PORT}/info")
    print(f"   Retrieval endpoint: http://localhost:{PORT}/retrieval")
    print()

    app.run(host='0.0.0.0', port=PORT, debug=False)
