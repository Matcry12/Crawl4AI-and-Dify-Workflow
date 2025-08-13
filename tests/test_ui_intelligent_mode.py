#!/usr/bin/env python3
"""
Test script to verify the UI integration of intelligent RAG mode.
Run the Flask app and use this to see the features in action.
"""

import time
import requests
import json

def test_ui_endpoints():
    """Test that the UI endpoints work with intelligent mode parameters."""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing UI Integration for Intelligent RAG Mode")
    print("=" * 60)
    
    # Test data with intelligent mode enabled
    test_data = {
        "url": "https://example.com/docs",
        "max_pages": 2,
        "max_depth": 0,
        "api_key": "dataset-VoYPMEaQ8L1udk2F6oek99XK",
        "base_url": "http://localhost:8088",
        "llm_api_key": "",  # Will use from .env
        "extraction_model": "gemini/gemini-2.0-flash-exp",
        "naming_model": "gemini/gemini-1.5-flash",
        "knowledge_base_mode": "automatic",
        "selected_knowledge_base": None,
        "enable_dual_mode": True,
        "dual_mode_type": "intelligent",
        "word_threshold": 4000,
        "use_intelligent_mode": True,
        "intelligent_analysis_model": "gemini/gemini-1.5-flash"
    }
    
    print("\n📤 Sending test crawl request with intelligent mode...")
    print(f"   URL: {test_data['url']}")
    print(f"   Dual Mode: {test_data['enable_dual_mode']}")
    print(f"   Mode Type: {test_data['dual_mode_type']}")
    print(f"   Analysis Model: {test_data['intelligent_analysis_model']}")
    
    try:
        # Send crawl request
        response = requests.post(
            f"{base_url}/start_crawl",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("\n✅ Crawl started successfully!")
            result = response.json()
            print(f"   Response: {result}")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Connection error: {e}")
        print("   Make sure the Flask app is running (python app.py)")

def print_ui_instructions():
    """Print instructions for testing the UI manually."""
    print("\n" + "=" * 60)
    print("📋 Manual UI Testing Instructions")
    print("=" * 60)
    print("\n1. Start the Flask app:")
    print("   python app.py")
    print("\n2. Open browser to: http://localhost:5000")
    print("\n3. Click 'Advanced Settings' to expand options")
    print("\n4. Scroll down to 'RAG Optimization Mode' section")
    print("\n5. Test different modes:")
    print("   - Word Count Threshold (default)")
    print("   - AI-Powered Analysis (intelligent)")
    print("\n6. Watch the progress log for:")
    print("   - '🔀 Dual-Mode RAG: ENABLED'")
    print("   - '🤖 Using AI-powered content analysis'")
    print("   - '⏭️ Skipping page:' messages for low-value content")
    print("   - Mode selection decisions for each page")
    print("\n✨ The UI now supports all intelligent RAG features!")

if __name__ == "__main__":
    print_ui_instructions()
    
    # Optional: Test the API endpoint
    user_input = input("\nTest API endpoint? (y/n): ")
    if user_input.lower() == 'y':
        test_ui_endpoints()