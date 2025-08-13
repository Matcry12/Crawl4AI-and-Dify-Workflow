#!/usr/bin/env python3
"""
Test script for parent-child chunking functionality
"""

import asyncio
import json
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from models.schemas import ResultSchema
import os
from dotenv import load_dotenv

async def test_parent_child_extraction():
    """Test the parent-child chunking with a sample URL."""
    
    load_dotenv(override=True)
    
    # Test URL - you can change this to any documentation page
    test_url = "https://docs.python.org/3/tutorial/introduction.html"
    
    # Load the parent-child extraction prompt
    with open("prompts/extraction_prompt_parent_child.txt", "r") as f:
        instruction = f.read()
    
    # Configure browser
    browser_config = BrowserConfig(
        headless=True,
        verbose=False
    )
    
    # Configure LLM extraction
    llm_strategy = LLMExtractionStrategy(
        llm_config={
            "provider": "gemini/gemini-2.0-flash-exp",
            "api_token": os.getenv('GEMINI_API_KEY')
        },
        schema=ResultSchema.model_json_schema(),
        extraction_type="schema",
        instruction=instruction,
        chunk_token_threshold=1000000,
        overlap_rate=0.0,
        apply_chunking=False,
        extra_args={
            "temperature": 0.0,
            "max_tokens": 32000
        }
    )
    
    # Configure crawler
    crawler_config = CrawlerRunConfig(
        extraction_strategy=llm_strategy
    )
    
    # Extract content
    async with AsyncWebCrawler(config=browser_config) as crawler:
        print(f"🔍 Testing parent-child extraction on: {test_url}")
        print("-" * 80)
        
        result = await crawler.arun(url=test_url, config=crawler_config)
        
        if result.success and result.extracted_content:
            # Parse the extracted content
            if isinstance(result.extracted_content, str):
                extracted_data = json.loads(result.extracted_content)
            else:
                extracted_data = result.extracted_content
            
            if isinstance(extracted_data, list):
                extracted_data = extracted_data[0] if extracted_data else {}
            
            # Analyze the structure
            if extracted_data:
                title = extracted_data.get('title', 'No title')
                description = extracted_data.get('description', '')
                
                print(f"✅ Extraction successful!")
                print(f"📄 Title: {title}")
                print(f"📏 Total content length: {len(description)} characters")
                
                # Count parent and child sections
                parent_count = description.count('###PARENT_SECTION###') + 1
                child_count = description.count('###CHILD_SECTION###')
                
                print(f"📊 Structure:")
                print(f"   - Parent sections: {parent_count}")
                print(f"   - Child sections: {child_count}")
                print(f"   - Average children per parent: {child_count / parent_count:.1f}")
                
                # Extract and display section titles
                print("\n📚 Section Hierarchy:")
                lines = description.split('\n')
                current_parent = None
                
                for line in lines:
                    if '###PARENT_SECTION###' in line:
                        # Extract parent title
                        if '[' in line and ']' in line:
                            title_start = line.find('[') + 1
                            title_end = line.find(']')
                            current_parent = line[title_start:title_end]
                            print(f"\n🔸 PARENT: {current_parent}")
                    elif '###CHILD_SECTION###' in line:
                        # Extract child title
                        if '[' in line and ']' in line:
                            title_start = line.find('[') + 1
                            title_end = line.find(']')
                            child_title = line[title_start:title_end]
                            print(f"   └─ CHILD: {child_title}")
                
                # Save sample output
                output_file = "test_parent_child_output.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'url': test_url,
                        'title': title,
                        'parent_sections': parent_count,
                        'child_sections': child_count,
                        'total_length': len(description),
                        'content': description[:2000] + '...' if len(description) > 2000 else description
                    }, f, indent=2, ensure_ascii=False)
                
                print(f"\n💾 Sample output saved to: {output_file}")
                
                # Display a snippet of the content structure
                print("\n📝 Content preview (first 500 chars):")
                print("-" * 80)
                print(description[:500] + "...")
                
        else:
            print("❌ Extraction failed")
            if hasattr(result, 'error_message'):
                print(f"Error: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(test_parent_child_extraction())