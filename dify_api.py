#!/usr/bin/env python3
"""
Dify External Knowledge API Wrapper
Provides a REST API endpoint compatible with Dify.ai's External Knowledge API specification.
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
DEFAULT_SEARCH_LEVEL = os.getenv('SEARCH_LEVEL', 'section')  # document, section, or proposition
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
print("🚀 Dify External Knowledge API Server")
print("=" * 80)
print(f"Knowledge ID: {KNOWLEDGE_ID}")
print(f"Search Level: {DEFAULT_SEARCH_LEVEL}")
print(f"Port: {PORT}")
print(f"API Key configured: {'✅' if API_KEY and API_KEY != 'your-secret-api-key-here' else '❌'}")
print("=" * 80)
print()


def verify_api_key(auth_header: Optional[str]) -> tuple[bool, Optional[str]]:
    """
    Verify the API key from Authorization header.

    Returns:
        (is_valid, error_message)
    """
    if not auth_header:
        return False, "Missing Authorization header"

    # Expected format: "Bearer <api-key>"
    parts = auth_header.split(' ')
    if len(parts) != 2 or parts[0] != 'Bearer':
        return False, "Invalid Authorization header format. Expected 'Bearer <api-key>'"

    api_key = parts[1]
    if api_key != API_KEY:
        return False, "Invalid API key"

    return True, None


def search_knowledge(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.0,
    search_level: str = None,
    mode_filter: str = None
) -> List[Dict]:
    """
    Search the knowledge base using RAG system.

    Args:
        query: User's question
        top_k: Number of results to return
        score_threshold: Minimum similarity score (0-1)
        search_level: Level to search (document/section/proposition)
        mode_filter: Filter by mode (paragraph/full-doc)

    Returns:
        List of records with content, score, title, and metadata
    """
    # Use configured default if not specified
    if not search_level:
        search_level = DEFAULT_SEARCH_LEVEL

    # Generate embedding for query
    query_embedding = searcher.create_embedding(query)
    if not query_embedding:
        return []

    # Search using appropriate level
    if search_level == "section":
        results = db.search_similar_sections(
            query_embedding=query_embedding,
            mode=mode_filter,
            limit=top_k,
            min_similarity=score_threshold
        )
    elif search_level == "proposition":
        results = db.search_similar_propositions(
            query_embedding=query_embedding,
            mode=mode_filter,
            limit=top_k,
            min_similarity=score_threshold
        )
    else:  # document
        results = db.search_similar_documents(
            query_embedding=query_embedding,
            mode=mode_filter,
            limit=top_k,
            min_similarity=score_threshold
        )

    # Convert to Dify format
    records = []
    for result in results:
        # Build metadata
        metadata = {}

        if search_level == "section":
            metadata = {
                "document_id": result.get('document_id', ''),
                "document_title": result.get('document_title', ''),
                "document_mode": result.get('document_mode', ''),
                "section_index": result.get('section_index', 0),
                "section_id": result.get('id', ''),
                "keywords": result.get('keywords', ''),
                "topics": result.get('topics', ''),
                "section_type": result.get('section_type', ''),
                "chunk_type": "section"
            }
            title = f"{result.get('document_title', 'Unknown')} - Section {result.get('section_index', 0)}"
            content = result.get('content', '')

        elif search_level == "proposition":
            metadata = {
                "document_id": result.get('document_id', ''),
                "document_title": result.get('document_title', ''),
                "document_mode": result.get('document_mode', ''),
                "section_id": result.get('section_id', ''),
                "section_index": result.get('section_index', 0),
                "proposition_index": result.get('proposition_index', 0),
                "proposition_type": result.get('proposition_type', ''),
                "entities": result.get('entities', ''),
                "keywords": result.get('keywords', ''),
                "chunk_type": "proposition"
            }
            title = f"{result.get('document_title', 'Unknown')} - Proposition {result.get('proposition_index', 0)}"
            content = result.get('content', '')

        else:  # document
            metadata = {
                "document_id": result.get('id', ''),
                "category": result.get('category', ''),
                "mode": result.get('mode', ''),
                "chunk_type": "document"
            }
            title = result.get('title', 'Untitled')
            # For documents, use summary as primary content, full content as fallback
            content = result.get('summary', '') or result.get('content', '')

        records.append({
            "content": content,
            "score": result.get('similarity', 0.0),
            "title": title,
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
    is_valid, error_msg = verify_api_key(auth_header)

    if not is_valid:
        return jsonify({
            "error_code": 1001 if "format" in error_msg else 1002,
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
    search_level = data.get('search_level', DEFAULT_SEARCH_LEVEL)
    mode_filter = data.get('mode_filter')  # paragraph or full-doc

    # Search knowledge base
    try:
        records = search_knowledge(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            search_level=search_level,
            mode_filter=mode_filter
        )

        print(f"📝 Query: {query[:50]}...")
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
        "search_level": DEFAULT_SEARCH_LEVEL
    }), 200


@app.route('/info', methods=['GET'])
def info():
    """API information endpoint."""
    # Check if API key is in header for protected info
    auth_header = request.headers.get('Authorization')
    is_valid, _ = verify_api_key(auth_header)

    # Count available data
    try:
        doc_count = len(db.get_all_documents_with_embeddings())
    except:
        doc_count = "unknown"

    info_data = {
        "api_version": "1.0.0",
        "knowledge_id": KNOWLEDGE_ID,
        "default_search_level": DEFAULT_SEARCH_LEVEL,
        "supported_search_levels": ["document", "section", "proposition"],
        "supported_modes": ["paragraph", "full-doc"],
        "endpoint": "/retrieval"
    }

    # Add detailed stats only if authenticated
    if is_valid:
        info_data["documents"] = doc_count
        info_data["database"] = "PostgreSQL with pgvector"
        info_data["index_type"] = "HNSW"

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
