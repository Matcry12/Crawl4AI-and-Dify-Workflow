#!/usr/bin/env python3
"""
Main entry point for Crawl4AI application.
Starts the Flask UI server.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the UI app
from ui.app import app

if __name__ == '__main__':
    print("🚀 Starting Crawl4AI UI Server...")
    print("📍 Access the UI at: http://localhost:5000")
    app.run(debug=True, threaded=True, port=5000)
