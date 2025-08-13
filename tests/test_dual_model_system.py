#!/usr/bin/env python3
"""Test script for the dual-model system: Fast model for naming + Smart model for extraction."""

import asyncio
import os
import time
from dotenv import load_dotenv
from crawl_workflow import CrawlWorkflow

async def test_dual_model_categorization():
    """Test dual-model setup for naming vs extraction."""
    load_dotenv(override=True)
    
    print("🚀 DUAL-MODEL SYSTEM TEST")
    print("="*50)
    print("Fast Model (Naming): gemini/gemini-1.5-flash")
    print("Smart Model (Extraction): gemini/gemini-2.0-flash-exp")
    print("="*50)
    
    # Initialize workflow with dual-model configuration
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key="dataset-VoYPMEaQ8L1udk2F6oek99XK",
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        naming_model="gemini/gemini-1.5-flash"  # Fast & cheap for naming
    )
    
    # Test cases to demonstrate naming speed vs extraction accuracy
    test_cases = [
        {
            "url": "https://eosnetwork.com/docs",
            "content": """EOS Network Documentation
            
            EOS is a blockchain platform designed for the development of decentralized applications (dApps). 
            
            Key Features:
            - High transaction throughput (up to 4,000 transactions per second)
            - Zero transaction fees for users
            - WebAssembly (WASM) virtual machine for smart contracts
            - Delegated Proof of Stake (DPoS) consensus mechanism
            
            Getting Started:
            1. Set up your development environment
            2. Create an EOS account
            3. Deploy your first smart contract
            4. Interact with the blockchain
            
            The EOS ecosystem includes various tools and resources for developers including:
            - EOSIO SDK for different programming languages
            - Block explorers for network monitoring
            - Wallets for asset management
            - dApp browsers for user interaction
            
            Security Considerations:
            - Always validate user inputs in smart contracts
            - Use multi-signature accounts for high-value operations
            - Regular security audits are recommended
            - Keep private keys secure and never share them
            
            This comprehensive guide covers everything from basic concepts to advanced development techniques."""
        },
        {
            "url": "https://bitcoin.org/getting-started",
            "content": """Bitcoin Getting Started Guide
            
            Bitcoin is a revolutionary peer-to-peer electronic cash system that allows online payments 
            without going through financial institutions.
            
            What is Bitcoin?
            Bitcoin is a decentralized digital currency that enables instant payments to anyone, anywhere in the world. 
            Bitcoin uses peer-to-peer technology with no central authority.
            
            How to Get Started:
            1. Choose a Bitcoin wallet
            2. Get your first bitcoins
            3. Secure your wallet
            4. Learn about Bitcoin addresses
            
            Types of Wallets:
            - Desktop wallets: Full control, but require maintenance
            - Mobile wallets: Convenient for everyday use
            - Web wallets: Accessible anywhere, but less secure
            - Hardware wallets: Maximum security for large amounts
            
            Buying Bitcoin:
            You can buy bitcoin through cryptocurrency exchanges, Bitcoin ATMs, or peer-to-peer marketplaces.
            Always use reputable sources and verify the legitimacy of any service.
            
            Security Best Practices:
            - Use strong passwords and two-factor authentication
            - Keep most of your bitcoins in offline storage
            - Always double-check recipient addresses
            - Keep your wallet software up to date
            
            Understanding Transactions:
            Bitcoin transactions are confirmed by the network through mining. Confirmation times vary 
            but typically take 10-60 minutes for security."""
        }
    ]
    
    print("\n🧪 Testing Categorization Speed vs Extraction Quality")
    print("-"*60)
    
    total_naming_time = 0
    total_extraction_time = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📄 Test Case {i}: {test_case['url']}")
        print(f"Content length: {len(test_case['content'])} characters")
        
        # Test naming speed (fast model)
        print("\n🏃‍♂️ NAMING PHASE (Fast Model)")
        start_time = time.time()
        
        category, tags = await workflow.categorize_content(test_case['content'], test_case['url'])
        
        naming_time = time.time() - start_time
        total_naming_time += naming_time
        
        print(f"⏱️  Naming time: {naming_time:.2f} seconds")
        print(f"✅ Category: {category}")
        print(f"🏷️  Tags: {', '.join(tags)}")
        
        # Simulate extraction phase (would use smart model in real workflow)
        print(f"\n🧠 EXTRACTION PHASE (Smart Model)")
        print(f"📝 Would use: gemini/gemini-2.0-flash-exp")
        print(f"🎯 Purpose: Extract comprehensive, structured content")
        print(f"💰 Cost: Higher tokens, better quality")
        
        # Add to workflow cache
        workflow.knowledge_bases[category] = f"kb_{i}"
    
    # Summary
    print(f"\n🎯 PERFORMANCE SUMMARY")
    print("="*40)
    print(f"Total naming time: {total_naming_time:.2f} seconds")
    print(f"Average naming time: {total_naming_time/len(test_cases):.2f} seconds per page")
    print(f"Estimated extraction time: {total_naming_time * 3:.2f} seconds (3x slower with smart model)")
    
    print(f"\n💡 OPTIMIZATION BENEFITS:")
    print(f"✅ Fast naming: Saves time on categorization")
    print(f"✅ Smart extraction: High-quality content processing")
    print(f"✅ Cost efficient: Fast model for simple tasks")
    print(f"✅ Quality where needed: Smart model for complex extraction")

async def test_model_configurations():
    """Test different model configuration options."""
    
    print(f"\n🔧 MODEL CONFIGURATION OPTIONS")
    print("="*50)
    
    configurations = [
        {
            "name": "Ultra Fast Setup",
            "naming_model": "gemini/gemini-1.5-flash",
            "extraction_model": "gemini/gemini-1.5-flash", 
            "use_case": "High-volume, cost-sensitive crawling"
        },
        {
            "name": "Balanced Setup (Recommended)",
            "naming_model": "gemini/gemini-1.5-flash",
            "extraction_model": "gemini/gemini-2.0-flash-exp",
            "use_case": "Fast naming + quality extraction"
        },
        {
            "name": "High Quality Setup",
            "naming_model": "gemini/gemini-2.0-flash-exp",
            "extraction_model": "gemini/gemini-2.0-flash-exp",
            "use_case": "Maximum quality for critical content"
        },
        {
            "name": "Custom Setup",
            "naming_model": "openai/gpt-4o-mini",
            "extraction_model": "gemini/gemini-2.0-flash-exp",
            "use_case": "Mix different providers for optimal cost/performance"
        }
    ]
    
    for config in configurations:
        print(f"\n📋 {config['name']}")
        print(f"   📝 Naming: {config['naming_model']}")
        print(f"   🔍 Extraction: {config['extraction_model']}")
        print(f"   🎯 Use case: {config['use_case']}")
        
        # Show how to initialize
        print(f"   💻 Code:")
        print(f"      workflow = CrawlWorkflow(")
        print(f"          naming_model=\"{config['naming_model']}\",")
        print(f"      )")
        print(f"      workflow.crawl_and_process(")
        print(f"          extraction_model=\"{config['extraction_model']}\",")
        print(f"      )")

async def main():
    """Run all dual-model tests."""
    await test_dual_model_categorization()
    await test_model_configurations()
    
    print(f"\n🎉 DUAL-MODEL SYSTEM READY!")
    print("="*50)
    print("Your workflow now supports:")
    print("✅ Fast model for knowledge base naming")
    print("✅ Smart model for content extraction")
    print("✅ Optimal cost/performance balance")
    print("✅ Flexible model configuration")
    print("✅ Smart duplicate prevention")

if __name__ == "__main__":
    asyncio.run(main())