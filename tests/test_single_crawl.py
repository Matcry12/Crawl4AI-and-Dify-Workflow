#!/usr/bin/env python3
"""
Simple test script for crawling a single website.
This is for testing purposes only and will not be committed to git.
"""

import asyncio
import os
from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler
from datetime import datetime
from urllib.parse import urlparse

async def crawl_single_page(url: str):
    """Crawl a single webpage and display results."""
    print(f"🕷️  Starting crawl for: {url}")
    print("=" * 60)
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        try:
            # Perform the crawl
            result = await crawler.arun(url=url)
            
            if result.success:
                print(f"\n✅ Successfully crawled: {url}")
                print(f"Title: {result.metadata.get('title', 'N/A')}")
                print(f"Content length: {len(result.markdown)} characters")
                print(f"Links found: {len(result.links)}")
                
                # Display first 500 characters of content
                print("\n📄 Content preview:")
                print("-" * 40)
                #print(result.markdown)
                print(result.markdown[:500] + "..." if len(result.markdown) > 500 else result.markdown)
                print("-" * 40)
                
                # Show some extracted links
                if hasattr(result, 'links') and result.links:
                    try:
                        print(f"\n🔗 First 5 links found:")
                        link_list = list(result.links) if not isinstance(result.links, list) else result.links
                        for i, link in enumerate(link_list[:5], 1):
                            print(f"  {i}. {link}")
                    except Exception as e:
                        print(f"Error displaying links: {e}")
                
                # Save to markdown file
                output_dir = "output"
                os.makedirs(output_dir, exist_ok=True)
                
                # Generate filename based on URL and timestamp
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.replace(".", "_")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{domain}_{timestamp}.md"
                filepath = os.path.join(output_dir, filename)
                
                # Write markdown content to file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# {result.metadata.get('title', 'Untitled')}\n\n")
                    f.write(f"**URL:** {url}\n")
                    f.write(f"**Crawled at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("---\n\n")
                    f.write(result.markdown)
                
                print(f"\n💾 Saved to: {filepath}")
            else:
                print(f"\n❌ Failed to crawl: {url}")
                print(f"Error: {result.error_message}")
                
        except Exception as e:
            print(f"\n🚨 Exception occurred: {str(e)}")

async def main():
    """Main function to run the test crawl."""
    # Load environment variables
    load_dotenv(override=True)
    
    print("🧪 Crawl4AI Single Website Test")
    print("=" * 60)
    
    # Test URL - using a simple, reliable website
    test_url = "https://docln.sbs/truyen/139-that-nghiep-tai-sinh/c6767-web-novel-chapter-12-co-gai-tre-hung-du"
    
    # You can change this to test different websites
    # test_url = "https://docs.python.org/3/"
    # test_url = "https://github.com"
    
    await crawl_single_page(test_url)
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(main())