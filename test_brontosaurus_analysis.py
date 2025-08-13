#!/usr/bin/env python3
"""Test the intelligent content analyzer with the Brontosaurus page."""

import asyncio
from intelligent_content_analyzer import IntelligentContentAnalyzer
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

async def test_brontosaurus_page():
    """Test analysis of the Brontosaurus wiki page."""
    url = "https://growagarden.fandom.com/wiki/Brontosaurus"
    
    print(f"🦕 Testing content analysis for: {url}")
    print("=" * 80)
    
    # First, crawl the page to get the content
    browser_config = BrowserConfig(headless=True, verbose=False)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url)
        
        if result.success and result.markdown:
            print(f"✅ Successfully crawled page")
            print(f"📄 Content length: {len(result.markdown)} characters")
            print(f"\n📝 First 500 chars of content:")
            print("-" * 40)
            print(result.markdown[:500])
            print("-" * 40)
            
            # Initialize analyzer (using API key from environment)
            import os
            api_key = os.getenv('GEMINI_API_KEY', 'YOUR_API_KEY_HERE')
            analyzer = IntelligentContentAnalyzer(
                llm_api_key=api_key,
                analysis_model="gemini/gemini-1.5-flash"
            )
            
            # Analyze the content
            print(f"\n🔍 Running intelligent analysis...")
            try:
                analysis = await analyzer.analyze_content(url, result.markdown)
                
                print(f"\n📊 Analysis Results:")
                print(f"   Content Value: {analysis.get('content_value', 'unknown').upper()}")
                print(f"   Value Reason: {analysis.get('value_reason', 'N/A')}")
                print(f"   Content Structure: {analysis.get('content_structure', 'unknown').upper()}")
                print(f"   Structure Reason: {analysis.get('structure_reason', 'N/A')}")
                print(f"   Recommended Mode: {analysis.get('recommended_mode', 'unknown').upper()}")
                print(f"   Mode Reason: {analysis.get('mode_reason', 'N/A')}")
                print(f"   Content Type: {analysis.get('content_type', 'N/A')}")
                print(f"   Main Topics: {', '.join(analysis.get('main_topics', []))}")
                
                # Determine final processing mode
                mode, reason = analyzer.determine_processing_mode(analysis)
                print(f"\n🎯 Final Decision:")
                print(f"   Processing Mode: {mode.upper()}")
                print(f"   Reason: {reason}")
                
                # Check if it correctly identified as single topic
                if analysis.get('content_structure') == 'single_topic' and analysis.get('recommended_mode') == 'full_doc':
                    print(f"\n✅ SUCCESS: Correctly identified Brontosaurus page as SINGLE_TOPIC requiring FULL_DOC mode!")
                else:
                    print(f"\n❌ ISSUE: Page should be SINGLE_TOPIC with FULL_DOC mode")
                    
            except Exception as e:
                print(f"❌ Analysis failed: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"❌ Failed to crawl page")

if __name__ == "__main__":
    # Note: You need to set your API key as environment variable or replace above
    import os
    if not os.getenv('GEMINI_API_KEY'):
        print("⚠️  Please set GEMINI_API_KEY environment variable or update the script with your API key")
        print("   Example: export GEMINI_API_KEY='your-api-key-here'")
    else:
        asyncio.run(test_brontosaurus_page())