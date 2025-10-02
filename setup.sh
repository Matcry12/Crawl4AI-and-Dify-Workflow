#!/bin/bash
# Crawl4AI Setup Script
# This script installs all dependencies including Playwright browsers

set -e  # Exit on error

echo "🚀 Setting up Crawl4AI..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "📥 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo "🌐 Installing Playwright browsers (this may take a few minutes)..."
python -m playwright install chromium

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start using Crawl4AI:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Copy .env.example to .env: cp .env.example .env"
echo "  3. Configure your API keys in .env"
echo "  4. Run the app: python app.py"