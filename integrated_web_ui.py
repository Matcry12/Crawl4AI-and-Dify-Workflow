#!/usr/bin/env python3
"""
Integrated Web UI for RAG Pipeline
Combines Document Viewer + Workflow Manager in one interface
"""

import os
import sys
import asyncio
import threading
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from datetime import datetime
import json
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chunked_document_database import SimpleDocumentDatabase

app = Flask(__name__)
db = SimpleDocumentDatabase()

# Global state for workflow execution
workflow_state = {
    'running': False,
    'progress': [],
    'logs': [],  # Detailed console logs
    'result': None,
    'error': None,
    'start_time': None,
    'end_time': None,
    'config': None,
    'current_step': None
}

# HTML template with navigation
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAG Pipeline Manager</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 30px;
        }

        .header h1 {
            font-size: 2em;
            margin-bottom: 5px;
        }

        .header p {
            opacity: 0.9;
            font-size: 0.95em;
        }

        .nav {
            background: #5568d3;
            display: flex;
            padding: 0;
            margin: 0;
        }

        .nav a {
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
        }

        .nav a:hover {
            background: rgba(255,255,255,0.1);
        }

        .nav a.active {
            background: white;
            color: #667eea;
            border-bottom: 3px solid #667eea;
        }

        .content {
            padding: 30px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            font-weight: bold;
            margin-bottom: 8px;
            color: #333;
        }

        .form-group input[type="text"],
        .form-group input[type="number"],
        .form-group select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }

        .form-group input:focus,
        .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }

        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 5px;
        }

        .checkbox-group input[type="checkbox"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }

        .checkbox-group label {
            margin: 0 !important;
            cursor: pointer;
        }

        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .btn-danger {
            background: #dc3545;
            color: white;
        }

        .btn-danger:hover {
            background: #c82333;
        }

        .status-box {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
        }

        .status-box h3 {
            margin-bottom: 10px;
            color: #333;
        }

        .progress-log {
            background: #1e1e1e;
            color: #00ff00;
            padding: 15px;
            border-radius: 8px;
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.6;
        }

        .progress-log p {
            margin: 3px 0;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border: 2px solid #e0e0e0;
        }

        .stat-card .value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }

        .stat-card .label {
            color: #666;
            margin-top: 5px;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 1px;
        }

        .document-list {
            margin-top: 20px;
        }

        .document-item {
            background: #f8f9fa;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }

        .document-item h4 {
            color: #333;
            margin-bottom: 5px;
        }

        .document-item p {
            color: #666;
            font-size: 0.9em;
        }

        .alert {
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .alert-success {
            background: #d4edda;
            border-left: 4px solid #28a745;
            color: #155724;
        }

        .alert-error {
            background: #f8d7da;
            border-left: 4px solid #dc3545;
            color: #721c24;
        }

        .alert-info {
            background: #d1ecf1;
            border-left: 4px solid #17a2b8;
            color: #0c5460;
        }

        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .config-display {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }

        .config-display pre {
            margin: 0;
            color: #333;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 RAG Pipeline Manager</h1>
            <p>Workflow Automation + Document Viewer</p>
        </div>

        <div class="nav">
            <a href="/" class="{{ 'active' if page == 'workflow' else '' }}">⚙️ Workflow</a>
            <a href="/documents" class="{{ 'active' if page == 'documents' else '' }}">📄 Documents</a>
            <a href="/stats" class="{{ 'active' if page == 'stats' else '' }}">📊 Statistics</a>
        </div>

        <div class="content">
            {% block content %}{% endblock %}
        </div>
    </div>

    <script>
        // Auto-scroll log to bottom
        function scrollLogToBottom() {
            const logDiv = document.getElementById('liveLog');
            if (logDiv) {
                logDiv.scrollTop = logDiv.scrollHeight;
            }
        }

        // Auto-refresh progress if workflow is running
        {% if page == 'workflow' %}
        let lastLogCount = {{ workflow_state['logs']|length }};

        function refreshProgress() {
            fetch('/api/workflow/status')
                .then(r => r.json())
                .then(data => {
                    if (data.running) {
                        // Check if new logs arrived
                        if (data.logs && data.logs.length > lastLogCount) {
                            // Update logs without full page reload
                            updateLogs(data.logs);
                            lastLogCount = data.logs.length;
                        } else if (data.logs.length !== lastLogCount) {
                            // Full reload if state changed significantly
                            location.reload();
                        }
                    } else {
                        // Workflow finished, reload to show results
                        location.reload();
                    }
                });
        }

        function updateLogs(logs) {
            const logDiv = document.getElementById('liveLog');
            if (logDiv) {
                // Keep scroll position if user has scrolled up
                const wasScrolledToBottom = logDiv.scrollHeight - logDiv.scrollTop <= logDiv.clientHeight + 50;

                logDiv.innerHTML = '';
                logs.forEach(log => {
                    const p = document.createElement('p');
                    p.textContent = log;
                    logDiv.appendChild(p);
                });

                // Auto-scroll if was at bottom
                if (wasScrolledToBottom) {
                    scrollLogToBottom();
                }
            }
        }

        const isRunning = {{ 'true' if workflow_state['running'] else 'false' }};
        if (isRunning) {
            setInterval(refreshProgress, 3000); // Check every 3 seconds
            // Auto-scroll on initial load
            setTimeout(scrollLogToBottom, 500);
        }
        {% endif %}
    </script>
</body>
</html>
"""

# Workflow page template
WORKFLOW_PAGE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', """
<h2>🔧 Workflow Configuration</h2>

{% if workflow_state['running'] %}
<div class="alert alert-info">
    <strong>⏳ Workflow Running...</strong><br>
    Started at: {{ workflow_state['start_time'] }}
    {% if workflow_state['current_step'] %}
    <br>Current Step: {{ workflow_state['current_step'] }}
    {% endif %}
</div>

<div class="status-box">
    <h3>📊 Progress Summary</h3>
    <div class="progress-log" style="max-height: 350px; overflow-y: auto; background: #f8f9fa; padding: 12px; border-radius: 6px;">
        {% for line in workflow_state['progress'] %}
        <p style="margin: 5px 0; font-family: 'Monaco', 'Menlo', monospace; font-size: 0.9em; line-height: 1.5;">{{ line }}</p>
        {% endfor %}
        {% if workflow_state['progress']|length == 0 %}
        <p style="color: #888;">Initializing...</p>
        {% endif %}
    </div>
</div>

<div class="status-box" style="margin-top: 20px;">
    <h3>📜 Live Console Logs</h3>
    <div class="progress-log" id="liveLog" style="max-height: 600px; overflow-y: auto; background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 6px; font-family: 'Monaco', 'Menlo', monospace; font-size: 0.85em;">
        {% for log in workflow_state['logs'] %}
        <p style="margin: 3px 0; line-height: 1.4;">{{ log }}</p>
        {% endfor %}
        {% if workflow_state['logs']|length == 0 %}
        <p style="color: #888;">Waiting for logs...</p>
        {% endif %}
    </div>
    <button onclick="scrollLogToBottom()" style="margin-top: 10px; padding: 10px 18px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 0.95em;">
        ⬇️ Scroll to Bottom
    </button>
</div>

<form action="/workflow/stop" method="POST" style="margin-top: 20px;">
    <button type="submit" class="btn btn-danger">⏹ Stop Workflow</button>
</form>

{% elif workflow_state['result'] %}
<div class="alert alert-success">
    <strong>✅ Workflow Completed!</strong><br>
    Started: {{ workflow_state['start_time'] }}<br>
    Finished: {{ workflow_state['end_time'] }}<br>
    <a href="/" style="color: #155724; text-decoration: underline;">Run Another Workflow</a>
</div>

<div class="status-box">
    <h3>📊 Progress Summary</h3>
    <div class="progress-log" style="max-height: 400px; overflow-y: auto; background: #f8f9fa; padding: 15px; border-radius: 6px;">
        {% for line in workflow_state['progress'] %}
        <p style="margin: 5px 0; font-family: 'Monaco', 'Menlo', monospace; font-size: 0.9em;">{{ line }}</p>
        {% endfor %}
        {% if workflow_state['progress']|length == 0 %}
        <p style="color: #888;">No progress information</p>
        {% endif %}
    </div>
</div>

<div class="status-box" style="margin-top: 20px;">
    <h3>📜 Complete Console Logs</h3>
    <div class="progress-log" style="max-height: 600px; overflow-y: auto; background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 6px; font-family: 'Monaco', 'Menlo', monospace; font-size: 0.85em;">
        {% for log in workflow_state['logs'] %}
        <p style="margin: 3px 0; line-height: 1.4;">{{ log }}</p>
        {% endfor %}
        {% if workflow_state['logs']|length == 0 %}
        <p style="color: #888;">No logs available</p>
        {% endif %}
    </div>
</div>

<div class="status-box" style="margin-top: 20px;">
    <h3>📊 Results</h3>
    <div class="config-display">
        <pre>{{ workflow_state['result']|safe }}</pre>
    </div>
</div>

<form action="/workflow/clear" method="POST" style="margin-top: 20px;">
    <button type="submit" class="btn btn-primary">🔄 Clear and Start New</button>
</form>

{% elif workflow_state['error'] %}
<div class="alert alert-error">
    <strong>❌ Workflow Failed</strong><br>
    Started: {{ workflow_state['start_time'] }}<br>
    Failed at: {{ workflow_state['end_time'] }}<br>
    Error: {{ workflow_state['error'] }}
</div>

<div class="status-box">
    <h3>📊 Progress Summary (Before Failure)</h3>
    <div class="progress-log" style="max-height: 400px; overflow-y: auto; background: #fff3cd; padding: 15px; border-radius: 6px;">
        {% for line in workflow_state['progress'] %}
        <p style="margin: 5px 0; font-family: 'Monaco', 'Menlo', monospace; font-size: 0.9em;">{{ line }}</p>
        {% endfor %}
        {% if workflow_state['progress']|length == 0 %}
        <p style="color: #888;">No progress information</p>
        {% endif %}
    </div>
</div>

<div class="status-box" style="margin-top: 20px;">
    <h3>📜 Console Logs (Debug Information)</h3>
    <div class="progress-log" style="max-height: 600px; overflow-y: auto; background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 6px; font-family: 'Monaco', 'Menlo', monospace; font-size: 0.85em;">
        {% for log in workflow_state['logs'] %}
        <p style="margin: 3px 0; line-height: 1.4;">{{ log }}</p>
        {% endfor %}
        {% if workflow_state['logs']|length == 0 %}
        <p style="color: #888;">No logs available</p>
        {% endif %}
    </div>
</div>

<form action="/workflow/clear" method="POST" style="margin-top: 20px;">
    <button type="submit" class="btn btn-primary">🔄 Clear and Retry</button>
</form>

{% else %}
<form action="/workflow/start" method="POST">
    <div class="form-group">
        <label>🌐 Start URL</label>
        <input type="text" name="start_url"
               value="https://docs.eosnetwork.com/docs/latest/quick-start/"
               placeholder="https://example.com" required>
    </div>

    <div class="form-group">
        <label>📄 Max Pages to Crawl</label>
        <input type="number" name="max_pages" value="3" min="1" max="100" required>
    </div>

    <div class="form-group">
        <label>🤖 LLM Model</label>
        <select name="llm_model">
            <option value="gemini-2.0-flash-exp">Gemini 2.0 Flash (Experimental)</option>
            <option value="gemini-2.5-flash-lite" selected>Gemini 2.5 Flash Lite (Default)</option>
            <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
            <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
        </select>
    </div>

    <div class="form-group">
        <label>📁 Output Directory</label>
        <input type="text" name="output_dir" value="crawl_output" placeholder="output_directory">
    </div>

    <div class="form-group">
        <div class="checkbox-group">
            <input type="checkbox" id="same_domain" name="same_domain_only" checked>
            <label for="same_domain">🔒 Same Domain Only</label>
        </div>
    </div>

    <div class="form-group">
        <div class="checkbox-group">
            <input type="checkbox" id="extract_topics" name="extract_topics" checked>
            <label for="extract_topics">🏷️ Extract Topics</label>
        </div>
    </div>

    <div class="form-group">
        <div class="checkbox-group">
            <input type="checkbox" id="merge_decision" name="merge_decision" checked>
            <label for="merge_decision">🤔 Merge Decision Analysis</label>
        </div>
    </div>

    <div class="form-group">
        <div class="checkbox-group">
            <input type="checkbox" id="create_documents" name="create_documents" checked>
            <label for="create_documents">📝 Create New Documents</label>
        </div>
    </div>

    <div class="form-group">
        <div class="checkbox-group">
            <input type="checkbox" id="merge_documents" name="merge_documents" checked>
            <label for="merge_documents">🔀 Merge with Existing Documents</label>
        </div>
    </div>

    <button type="submit" class="btn btn-primary">🚀 Start Workflow</button>
</form>
{% endif %}
""")

# Documents page template
DOCUMENTS_PAGE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', """
<h2>📄 Documents in Database</h2>

<div class="stats-grid">
    <div class="stat-card">
        <div class="value">{{ stats['total_documents'] }}</div>
        <div class="label">Total Documents</div>
    </div>
    <div class="stat-card">
        <div class="value">{{ stats['total_chunks'] }}</div>
        <div class="label">Total Chunks</div>
    </div>
    <div class="stat-card">
        <div class="value">{{ (stats['total_chunks'] / stats['total_documents'])|round(1) if stats['total_documents'] > 0 else 0 }}</div>
        <div class="label">Avg Chunks/Doc</div>
    </div>
</div>

<div style="margin: 20px 0;">
    <input type="text" id="searchBox" placeholder="🔍 Search documents..."
           style="width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 14px;">
</div>

<div class="document-list" id="documentList">
    {% for doc in documents %}
    <div class="document-item" style="cursor: pointer;">
        <div onclick="toggleDocument('doc-{{ loop.index }}')">
            <h4>{{ doc['title'] }}</h4>
            <p>{{ doc.get('summary', 'No summary')[:200] }}{% if doc.get('summary', '')|length > 200 %}...{% endif %}</p>
            <p style="color: #999; font-size: 0.85em; margin-top: 5px;">
                Chunks: {{ doc.get('chunk_count', 0) }} |
                Keywords: {{ doc.get('keywords', [])|length }} |
                Content: {{ doc.get('content_length', 0) }} chars
            </p>
            <button onclick="event.stopPropagation(); loadDocumentDetails('doc-{{ loop.index }}', '{{ doc['id'] }}'); return false;"
                    id="btn-doc-{{ loop.index }}"
                    style="margin-top: 10px; padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">
                👁️ Show Full Details
            </button>
        </div>

        <div id="doc-{{ loop.index }}" style="display: none; margin-top: 15px; padding-top: 15px; border-top: 2px solid #e0e0e0;">
            <div style="text-align: center; padding: 40px;">
                <div class="spinner"></div>
                <p style="margin-top: 15px; color: #666;">Loading document details...</p>
            </div>
        </div>
    </div>
    {% endfor %}
</div>

<script>
// Cache loaded documents
const loadedDocs = new Set();

function loadDocumentDetails(elemId, docId) {
    const elem = document.getElementById(elemId);
    const btn = document.getElementById('btn-' + elemId);

    // If already visible, just hide it
    if (elem.style.display === 'block') {
        elem.style.display = 'none';
        btn.innerHTML = '👁️ Show Full Details';
        btn.style.background = '#667eea';
        return;
    }

    // Show the element
    elem.style.display = 'block';
    btn.innerHTML = '🔼 Hide Details';
    btn.style.background = '#dc3545';

    // If already loaded, don't fetch again
    if (loadedDocs.has(docId)) {
        return;
    }

    // Fetch full document details
    fetch('/api/document/' + encodeURIComponent(docId) + '/full')
        .then(response => response.json())
        .then(doc => {
            loadedDocs.add(docId);

            // Build HTML for full details
            let html = '';

            // Full Content
            html += '<h5 style="margin-bottom: 10px; color: #667eea;">📝 Full Content:</h5>';
            html += '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px; max-height: 400px; overflow-y: auto;">';
            html += '<pre style="white-space: pre-wrap; margin: 0; font-size: 0.9em; line-height: 1.6;">' + (doc.content || 'No content available') + '</pre>';
            html += '</div>';

            // Keywords
            if (doc.keywords && doc.keywords.length > 0) {
                html += '<h5 style="margin-top: 15px; margin-bottom: 10px; color: #667eea;">🏷️ Keywords:</h5>';
                html += '<div style="display: flex; flex-wrap: wrap; gap: 8px;">';
                doc.keywords.forEach(keyword => {
                    html += '<span style="background: #667eea; color: white; padding: 5px 12px; border-radius: 15px; font-size: 0.85em;">' + keyword + '</span>';
                });
                html += '</div>';
            }

            // Chunks
            const chunks = doc.chunks || [];
            html += '<h5 style="margin-top: 15px; margin-bottom: 10px; color: #667eea;">📦 Chunks (' + chunks.length + '):</h5>';

            if (chunks.length > 0) {
                chunks.forEach((chunk, idx) => {
                    html += '<div style="background: #fff3cd; padding: 12px; margin-bottom: 10px; border-radius: 6px; border: 2px solid #667eea;">';
                    html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">';
                    html += '<strong style="color: #667eea; font-size: 1.1em;">📦 Chunk ' + (chunk.chunk_index !== undefined ? chunk.chunk_index : idx + 1) + '</strong>';
                    html += '<div style="font-size: 0.85em; color: #666;">';
                    html += '<span style="background: #667eea; color: white; padding: 3px 8px; border-radius: 10px; margin-right: 5px;">' + (chunk.content ? chunk.content.length : 0) + ' chars</span>';
                    if (chunk.token_count) {
                        html += '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 10px;">' + chunk.token_count + ' tokens</span>';
                    }
                    html += '</div></div>';
                    html += '<div style="background: white; padding: 10px; border-radius: 4px; font-size: 0.9em; line-height: 1.6; max-height: 300px; overflow-y: auto;">';
                    html += (chunk.content || 'No content');
                    html += '</div></div>';
                });
            } else {
                html += '<div style="background: #f8d7da; padding: 15px; border-radius: 8px; border-left: 4px solid #dc3545; color: #721c24;">';
                html += '⚠️ No chunks available for this document';
                html += '</div>';
            }

            // Metadata
            html += '<p style="color: #999; font-size: 0.85em; margin-top: 15px;">';
            html += '<strong>ID:</strong> ' + doc.id + '<br>';
            if (doc.created_at) html += '<strong>Created:</strong> ' + doc.created_at + '<br>';
            if (doc.updated_at) html += '<strong>Updated:</strong> ' + doc.updated_at;
            html += '</p>';

            elem.innerHTML = html;
        })
        .catch(error => {
            elem.innerHTML = '<div style="background: #f8d7da; padding: 20px; border-radius: 8px; text-align: center; color: #721c24;">❌ Error loading document: ' + error + '</div>';
        });
}

// Search functionality
document.getElementById('searchBox').addEventListener('input', function(e) {
    const searchTerm = e.target.value.toLowerCase();
    const items = document.querySelectorAll('.document-item');

    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
});
</script>
""")

# Stats page template
STATS_PAGE = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', """
<h2>📊 Database Statistics</h2>

<div class="stats-grid">
    <div class="stat-card">
        <div class="value">{{ stats['total_documents'] }}</div>
        <div class="label">Documents</div>
    </div>
    <div class="stat-card">
        <div class="value">{{ stats['total_chunks'] }}</div>
        <div class="label">Chunks</div>
    </div>
    <div class="stat-card">
        <div class="value">{{ stats.get('avg_chunks_per_doc', 0)|round(1) }}</div>
        <div class="label">Avg Chunks/Doc</div>
    </div>
</div>

<div class="status-box" style="margin-top: 30px;">
    <h3>🗄️ Database Info</h3>
    <div class="config-display">
        <pre>Container: postgres-crawl4ai
Database: crawl4ai
Schema: Simplified (documents + chunks + merge_history)
Status: Connected ✅</pre>
    </div>
</div>
""")


# Routes
@app.route('/')
def index():
    """Workflow page"""
    return render_template_string(
        WORKFLOW_PAGE,
        page='workflow',
        workflow_state=workflow_state
    )


@app.route('/documents')
def documents():
    """Documents list page - lightweight view"""
    # Only get basic document info (no chunks) for fast loading
    docs_list = db.get_all_documents_with_embeddings()
    stats = db.get_stats()

    return render_template_string(
        DOCUMENTS_PAGE,
        page='documents',
        documents=docs_list,
        stats=stats
    )


@app.route('/api/document/<doc_id>/full')
def api_document_full(doc_id):
    """API endpoint to load full document details on demand"""
    from urllib.parse import unquote
    doc_id = unquote(doc_id)

    full_doc = db.get_document_by_id(doc_id)
    if full_doc:
        return jsonify(full_doc)
    else:
        return jsonify({'error': 'Document not found'}), 404


@app.route('/stats')
def stats():
    """Statistics page"""
    stats_data = db.get_stats()
    return render_template_string(
        STATS_PAGE,
        page='stats',
        stats=stats_data
    )


@app.route('/workflow/start', methods=['POST'])
def start_workflow():
    """Start workflow execution"""
    if workflow_state['running']:
        return redirect('/')

    # Get form data
    config = {
        'start_url': request.form.get('start_url'),
        'max_pages': int(request.form.get('max_pages', 3)),
        'llm_model': request.form.get('llm_model', 'gemini-2.5-flash-lite'),
        'output_dir': request.form.get('output_dir', 'crawl_output'),
        'same_domain_only': 'same_domain_only' in request.form,
        'extract_topics': 'extract_topics' in request.form,
        'merge_decision': 'merge_decision' in request.form,
        'create_documents': 'create_documents' in request.form,
        'merge_documents': 'merge_documents' in request.form
    }

    # Reset state
    workflow_state.update({
        'running': True,
        'progress': [f"Starting workflow at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
        'logs': [],
        'result': None,
        'error': None,
        'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'end_time': None,
        'config': config,
        'current_step': 'Initializing'
    })

    # Start workflow in background thread
    thread = threading.Thread(target=run_workflow_async, args=(config,))
    thread.daemon = True
    thread.start()

    return redirect('/')


@app.route('/workflow/stop', methods=['POST'])
def stop_workflow():
    """Stop workflow execution"""
    workflow_state['running'] = False
    workflow_state['progress'].append("⚠️ Workflow stopped by user")
    workflow_state['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return redirect('/')


@app.route('/workflow/clear', methods=['POST'])
def clear_workflow():
    """Clear workflow state"""
    workflow_state.update({
        'running': False,
        'progress': [],
        'logs': [],
        'result': None,
        'error': None,
        'start_time': None,
        'end_time': None,
        'config': None,
        'current_step': None
    })
    return redirect('/')


@app.route('/api/workflow/status')
def api_workflow_status():
    """API endpoint for workflow status"""
    return jsonify(workflow_state)


def run_workflow_async(config):
    """Run workflow in background thread"""
    import io
    import contextlib

    try:
        # Import workflow manager
        from workflow_manager import WorkflowManager

        # Add progress messages
        def add_progress(msg):
            workflow_state['progress'].append(f"[{time.strftime('%H:%M:%S')}] {msg}")

        def add_log(msg):
            """Add to detailed logs"""
            workflow_state['logs'].append(msg)

        add_progress(f"🌐 Crawling: {config['start_url']}")
        add_progress(f"📄 Max pages: {config['max_pages']}")
        add_progress(f"🤖 LLM Model: {config['llm_model']}")

        add_log(f"[{time.strftime('%H:%M:%S')}] ========================================")
        add_log(f"[{time.strftime('%H:%M:%S')}] WORKFLOW EXECUTION STARTED")
        add_log(f"[{time.strftime('%H:%M:%S')}] ========================================")
        add_log(f"[{time.strftime('%H:%M:%S')}] Start URL: {config['start_url']}")
        add_log(f"[{time.strftime('%H:%M:%S')}] Max Pages: {config['max_pages']}")
        add_log(f"[{time.strftime('%H:%M:%S')}] LLM Model: {config['llm_model']}")
        add_log(f"[{time.strftime('%H:%M:%S')}] Output Dir: {config['output_dir']}")
        add_log(f"[{time.strftime('%H:%M:%S')}] ========================================")

        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Initialize workflow
        add_progress("🔧 Initializing WorkflowManager...")
        add_log(f"[{time.strftime('%H:%M:%S')}] Initializing WorkflowManager...")
        workflow_state['current_step'] = "Initialization"

        workflow = WorkflowManager()

        # Set LLM model if specified
        if config.get('llm_model'):
            os.environ['LLM_MODEL'] = config['llm_model']

        add_progress("🚀 Starting workflow execution...")
        add_log(f"[{time.strftime('%H:%M:%S')}] Starting workflow execution...")
        workflow_state['current_step'] = "Crawling"

        # Capture stdout/stderr to logs
        class LogCapture:
            def write(self, text):
                if text and text.strip():
                    clean_text = text.rstrip('\n')
                    add_log(clean_text)

                    # Extract important progress messages for Progress Summary
                    # Match key workflow events
                    if any(marker in clean_text for marker in [
                        '🔵  STEP:',           # Workflow steps
                        '✅  [',               # Step completion
                        '✅ Page',             # Page completion
                        '✅ Extracted',        # Topic extraction
                        '✅ Created',          # Document creation
                        '✅ Merged',           # Document merging
                        '✅  ITERATIVE',       # Iterative completion
                        '❌',                  # Errors
                        '⚠️',                 # Warnings
                        'Total Results:',      # Final results
                        'Pages processed:',    # Stats
                        'Documents created:',  # Stats
                        'Documents merged:',   # Stats
                    ]):
                        # Add to progress summary (without excessive detail)
                        add_progress(clean_text.strip())

            def flush(self):
                pass

        # Redirect stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        log_capture = LogCapture()
        sys.stdout = log_capture
        sys.stderr = log_capture

        try:
            # Run workflow
            result = loop.run_until_complete(
                workflow.run(
                    start_url=config['start_url'],
                    max_pages=config['max_pages'],
                    same_domain_only=config['same_domain_only'],
                    output_dir=config['output_dir'],
                    extract_topics=config['extract_topics'],
                    merge_decision=config['merge_decision'],
                    create_documents=config['create_documents'],
                    merge_documents=config['merge_documents']
                )
            )
        finally:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        loop.close()

        # Format result
        result_text = json.dumps(result, indent=2) if result else "Workflow completed"

        add_log(f"[{time.strftime('%H:%M:%S')}] ========================================")
        add_log(f"[{time.strftime('%H:%M:%S')}] WORKFLOW COMPLETED SUCCESSFULLY")
        add_log(f"[{time.strftime('%H:%M:%S')}] ========================================")

        workflow_state.update({
            'running': False,
            'result': result_text,
            'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_step': 'Completed'
        })

        add_progress("✅ Workflow completed successfully!")

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()

        add_log(f"[{time.strftime('%H:%M:%S')}] ========================================")
        add_log(f"[{time.strftime('%H:%M:%S')}] ERROR OCCURRED")
        add_log(f"[{time.strftime('%H:%M:%S')}] ========================================")
        add_log(f"[{time.strftime('%H:%M:%S')}] {error_details}")

        workflow_state.update({
            'running': False,
            'error': str(e),
            'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_step': 'Failed'
        })
        workflow_state['progress'].append(f"❌ Error: {e}")


if __name__ == '__main__':
    print("=" * 80)
    print("🌐 Integrated RAG Pipeline Web UI")
    print("=" * 80)
    print()
    print("Starting web server...")
    print()
    print("✅ Server running at: http://localhost:5001")
    print()
    print("Features:")
    print("  • ⚙️  Workflow Manager - Configure and run crawl workflows")
    print("  • 📄 Document Viewer - Browse all documents in database")
    print("  • 📊 Statistics - View database metrics")
    print("  • 🔄 Real-time Progress - Watch workflow execution live")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 80)
    print()

    # Run server with auto-reload enabled
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=True, threaded=True)
