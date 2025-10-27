#!/usr/bin/env python3
"""
Simple Web UI for Document Viewer

A lightweight Flask web interface to view and explore documents in the database.
Features:
- Beautiful document list with search
- Document detail view with content and chunks
- Database statistics dashboard
- Auto-refresh support
- Mobile-friendly design
"""

import os
import sys
import asyncio
import threading
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chunked_document_database import SimpleDocumentDatabase


app = Flask(__name__)
db = SimpleDocumentDatabase()

# Global state for workflow execution
workflow_state = {
    'running': False,
    'progress': [],
    'result': None,
    'error': None,
    'start_time': None,
    'end_time': None
}


# HTML Templates
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Viewer - RAG Database</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .stat-card .value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }

        .stat-card .label {
            color: #6c757d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .controls {
            padding: 20px 30px;
            background: white;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }

        .search-box {
            flex: 1;
            min-width: 250px;
        }

        .search-box input {
            width: 100%;
            padding: 12px 20px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 1em;
            transition: all 0.3s;
        }

        .search-box input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .btn-secondary {
            background: #6c757d;
            color: white;
        }

        .btn-secondary:hover {
            background: #5a6268;
        }

        .content {
            padding: 30px;
        }

        .document-list {
            display: grid;
            gap: 20px;
        }

        .document-card {
            background: white;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            transition: all 0.3s;
            cursor: pointer;
        }

        .document-card:hover {
            border-color: #667eea;
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2);
        }

        .document-card .title {
            font-size: 1.3em;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }

        .document-card .meta {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-bottom: 10px;
            font-size: 0.9em;
            color: #6c757d;
        }

        .document-card .meta span {
            padding: 5px 10px;
            background: #f8f9fa;
            border-radius: 5px;
        }

        .document-card .keywords {
            margin-top: 10px;
        }

        .keyword-tag {
            display: inline-block;
            padding: 5px 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 15px;
            font-size: 0.85em;
            margin: 3px;
        }

        .document-card .summary {
            margin-top: 15px;
            color: #666;
            line-height: 1.6;
        }

        .document-detail {
            background: white;
            border-radius: 10px;
            padding: 30px;
        }

        .document-detail .section {
            margin-bottom: 30px;
        }

        .document-detail .section-title {
            font-size: 1.5em;
            color: #667eea;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }

        .document-detail .content-box {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            line-height: 1.8;
            white-space: pre-wrap;
        }

        .chunk-card {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 5px;
        }

        .chunk-card .chunk-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-weight: bold;
            color: #667eea;
        }

        .chunk-card .chunk-content {
            line-height: 1.6;
            color: #333;
            white-space: pre-wrap;
        }

        .back-btn {
            margin-bottom: 20px;
        }

        .no-results {
            text-align: center;
            padding: 60px 20px;
            color: #6c757d;
        }

        .no-results .icon {
            font-size: 4em;
            margin-bottom: 20px;
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.8em;
            }

            .stats {
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                padding: 20px;
            }

            .controls {
                flex-direction: column;
            }

            .search-box {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 Document Viewer</h1>
            <p>RAG Database Explorer - PostgreSQL + pgvector</p>
        </div>

        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

INDEX_TEMPLATE = BASE_TEMPLATE.replace(
    '{% block content %}{% endblock %}',
    """
        <div class="stats">
            <div class="stat-card">
                <div class="value">{{ stats.total_documents }}</div>
                <div class="label">Documents</div>
            </div>
            <div class="stat-card">
                <div class="value">{{ stats.total_chunks }}</div>
                <div class="label">Chunks</div>
            </div>
            <div class="stat-card">
                <div class="value">{{ stats.total_merges }}</div>
                <div class="label">Merges</div>
            </div>
            <div class="stat-card">
                <div class="value">{{ "%.1f"|format(stats.avg_chunks_per_doc) }}</div>
                <div class="label">Avg Chunks/Doc</div>
            </div>
        </div>

        <div class="controls">
            <div class="search-box">
                <form action="/" method="GET">
                    <input type="text" name="q" placeholder="🔍 Search documents by keyword..." value="{{ query or '' }}">
                </form>
            </div>
            <button class="btn btn-primary" onclick="location.reload()">🔄 Refresh</button>
        </div>

        <div class="content">
            {% if documents %}
                <div class="document-list">
                    {% for doc in documents %}
                    <div class="document-card" onclick="window.location='/document/{{ doc.id }}'">
                        <div class="title">{{ doc.title }}</div>
                        <div class="meta">
                            <span>📁 {{ doc.category }}</span>
                            <span>🏷️ {{ doc.keywords|length }} keywords</span>
                        </div>
                        <div class="keywords">
                            {% for keyword in doc.keywords[:5] %}
                            <span class="keyword-tag">{{ keyword }}</span>
                            {% endfor %}
                            {% if doc.keywords|length > 5 %}
                            <span class="keyword-tag">+{{ doc.keywords|length - 5 }} more</span>
                            {% endif %}
                        </div>
                        <div class="summary">{{ doc.summary[:200] }}{% if doc.summary|length > 200 %}...{% endif %}</div>
                    </div>
                    {% endfor %}
                </div>
            {% else %}
                <div class="no-results">
                    <div class="icon">🔍</div>
                    <h2>No documents found</h2>
                    <p>{% if query %}No documents match your search "{{ query }}"{% else %}The database is empty{% endif %}</p>
                </div>
            {% endif %}
        </div>
    """
)

DOCUMENT_TEMPLATE = BASE_TEMPLATE.replace(
    '{% block content %}{% endblock %}',
    """
        <div class="content">
            <div class="back-btn">
                <a href="/" class="btn btn-secondary">← Back to List</a>
            </div>

            <div class="document-detail">
                <h1 style="color: #333; margin-bottom: 20px;">{{ doc.title }}</h1>

                <div class="section">
                    <div class="meta" style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 20px;">
                        <span style="padding: 8px 15px; background: #f8f9fa; border-radius: 5px;">
                            📁 {{ doc.category }}
                        </span>
                        <span style="padding: 8px 15px; background: #f8f9fa; border-radius: 5px;">
                            🆔 {{ doc.id }}
                        </span>
                        <span style="padding: 8px 15px; background: #f8f9fa; border-radius: 5px;">
                            📅 {{ doc.created_at }}
                        </span>
                    </div>
                </div>

                {% if doc.keywords %}
                <div class="section">
                    <div class="section-title">🏷️ Keywords</div>
                    <div>
                        {% for keyword in doc.keywords %}
                        <span class="keyword-tag">{{ keyword }}</span>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}

                {% if doc.summary %}
                <div class="section">
                    <div class="section-title">📝 Summary</div>
                    <div class="content-box">{{ doc.summary }}</div>
                </div>
                {% endif %}

                <div class="section">
                    <div class="section-title">📄 Full Content ({{ doc.content|length }} characters)</div>
                    <div class="content-box">{{ doc.content }}</div>
                </div>

                {% if doc.chunks %}
                <div class="section">
                    <div class="section-title">🧩 Chunks ({{ doc.chunks|length }} total)</div>
                    {% for chunk in doc.chunks %}
                    <div class="chunk-card">
                        <div class="chunk-header">
                            <span>Chunk {{ chunk.chunk_index + 1 }}</span>
                            <span>{{ chunk.token_count }} tokens</span>
                        </div>
                        <div class="chunk-content">{{ chunk.content }}</div>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
        </div>
    """
)


@app.route('/')
def index():
    """Main page - document list with search"""
    query = request.args.get('q', '').strip()

    # Get stats
    stats = db.get_stats()
    if not stats:
        stats = {
            'total_documents': 0,
            'total_chunks': 0,
            'total_merges': 0,
            'avg_chunks_per_doc': 0.0
        }

    # Get documents
    all_docs = db.get_all_documents_with_embeddings()

    # Filter by query if provided
    if query:
        query_lower = query.lower()
        documents = []
        for doc in all_docs:
            title = doc.get('title', '').lower()
            keywords = [k.lower() for k in doc.get('keywords', [])]
            summary = doc.get('summary', '').lower()

            if (query_lower in title or
                any(query_lower in k for k in keywords) or
                query_lower in summary):
                documents.append(doc)
    else:
        documents = all_docs

    return render_template_string(
        INDEX_TEMPLATE,
        stats=stats,
        documents=documents,
        query=query
    )


@app.route('/document/<doc_id>')
def view_document(doc_id):
    """Document detail page"""
    try:
        # URL decode the doc_id in case it has special characters
        from urllib.parse import unquote
        doc_id = unquote(doc_id)

        doc = db.get_document_by_id(doc_id)

        if not doc:
            print(f"⚠️  Document not found: {doc_id}")
            return render_template_string(
                BASE_TEMPLATE.replace(
                    '{% block content %}{% endblock %}',
                    '''
                    <div class="content">
                        <div class="no-results">
                            <div class="icon">❌</div>
                            <h2>Document Not Found</h2>
                            <p>The requested document could not be found.</p>
                            <p style="color: #999; margin-top: 10px;">ID: {{ doc_id }}</p>
                            <br>
                            <a href="/" class="btn btn-primary">← Back to List</a>
                        </div>
                    </div>
                    '''
                ),
                doc_id=doc_id
            )

        return render_template_string(DOCUMENT_TEMPLATE, doc=doc)

    except Exception as e:
        print(f"❌ Error loading document {doc_id}: {e}")
        import traceback
        traceback.print_exc()

        return render_template_string(
            BASE_TEMPLATE.replace(
                '{% block content %}{% endblock %}',
                '''
                <div class="content">
                    <div class="no-results">
                        <div class="icon">⚠️</div>
                        <h2>Error Loading Document</h2>
                        <p>An error occurred while loading the document.</p>
                        <p style="color: #999; margin-top: 10px;">Error: {{ error }}</p>
                        <br>
                        <a href="/" class="btn btn-primary">← Back to List</a>
                    </div>
                </div>
                '''
            ),
            error=str(e)
        )


@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    stats = db.get_stats()
    return jsonify(stats)


@app.route('/api/documents')
def api_documents():
    """API endpoint for document list"""
    docs = db.get_all_documents_with_embeddings()
    return jsonify(docs)


@app.route('/api/document/<doc_id>')
def api_document(doc_id):
    """API endpoint for single document"""
    doc = db.get_document_by_id(doc_id)
    if doc:
        return jsonify(doc)
    else:
        return jsonify({'error': 'Document not found'}), 404


if __name__ == '__main__':
    print("=" * 80)
    print("🌐 Document Viewer Web UI")
    print("=" * 80)
    print()
    print("Starting web server...")
    print()
    print("✅ Server running at: http://localhost:5001")
    print("   Open this URL in your web browser")
    print()
    print("Features:")
    print("  • Beautiful document list with search")
    print("  • Click any document to view full details")
    print("  • View all chunks with token counts")
    print("  • Mobile-friendly responsive design")
    print("  • Real-time database statistics")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 80)
    print()

    # Run server
    app.run(host='0.0.0.0', port=5001, debug=False)
