#!/usr/bin/env python3
"""Test script to demonstrate LLM-based categorization for knowledge bases."""

import asyncio
import os
from dotenv import load_dotenv
from crawl_workflow import CrawlWorkflow

async def test_categorization():
    """Test the improved categorization with various content samples."""
    load_dotenv(override=True)
    
    # Initialize workflow
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key="dataset-VoYPMEaQ8L1udk2F6oek99XK",
        gemini_api_key=os.getenv('GEMINI_API_KEY')
    )
    
    # Test cases with different content types
    test_cases = [
        {
            "url": "https://eosnetwork.com/community",
            "content": "The EOS Network community has evolved through the contributions of numerous individuals worldwide. EOS is a blockchain platform designed for high performance and scalability. Join the EOS community discussions and shape the ecosystem's future."
        },
        {
            "url": "https://bitcoin.org/en/getting-started",
            "content": "Bitcoin is an innovative payment network and a new kind of money. Find all you need to know and get started with Bitcoin on bitcoin.org. Learn about wallets, buying bitcoin, and how to use it."
        },
        {
            "url": "https://docs.ethereum.org/developers/",
            "content": "Ethereum development documentation. Learn how to build decentralized applications on Ethereum. Smart contracts, Solidity programming, Web3.js integration and more."
        },
        {
            "url": "https://reactjs.org/tutorial/",
            "content": "React is a JavaScript library for building user interfaces. This tutorial will teach you React from scratch. Learn components, props, state, and hooks."
        },
        {
            "url": "https://api.example.com/docs",
            "content": "REST API documentation for our service. Endpoints include user authentication, data retrieval, and webhook management. All requests must include API key in headers."
        }
    ]
    
    print("🧪 Testing LLM-based categorization...\n")
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['url']}")
        print("-" * 50)
        
        try:
            category, tags = workflow.categorize_content(test['content'], test['url'])
            
            print(f"✅ Category: {category}")
            print(f"🏷️  Tags: {', '.join(tags)}")
            
            # Convert category to display name (what will be shown in Dify)
            kb_name = category.replace('_', ' ').title()
            print(f"📚 Knowledge Base Name: {kb_name}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n")
    
    print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_categorization())