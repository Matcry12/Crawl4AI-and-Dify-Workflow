#!/usr/bin/env python3
"""
BFS Web Crawler

Crawls websites using Breadth-First Search (BFS) algorithm.
Discovers and crawls all pages within the same domain.

Features:
- BFS traversal (level by level)
- Link discovery
- Domain filtering
- Progress tracking
- Saves all pages as markdown
- Generates detailed report
"""

import asyncio
from collections import deque
from urllib.parse import urljoin, urlparse
from pathlib import Path
from datetime import datetime
import json
import re
from typing import Set, Dict, List
import os

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode

# Import topic extractor
try:
    from extract_topics import TopicExtractor
    TOPIC_EXTRACTION_AVAILABLE = True
except ImportError:
    TOPIC_EXTRACTION_AVAILABLE = False


class BFSCrawler:
    """
    BFS Web Crawler

    Crawls websites using breadth-first search, discovering all linked pages
    within the same domain.
    """

    def __init__(
        self,
        start_url: str,
        max_pages: int = 50,
        same_domain_only: bool = True,
        output_dir: str = "bfs_crawled",
        extract_topics: bool = True
    ):
        """
        Initialize BFS Crawler

        Args:
            start_url: Starting URL to crawl
            max_pages: Maximum number of pages to crawl
            same_domain_only: Only crawl pages from same domain
            output_dir: Directory to save crawled pages
            extract_topics: Automatically extract topics after crawling
        """
        self.start_url = start_url
        self.max_pages = max_pages
        self.same_domain_only = same_domain_only
        self.output_dir = Path(output_dir)
        self.extract_topics = extract_topics

        # Parse start URL domain
        self.start_domain = urlparse(start_url).netloc

        # Non-content URL patterns to skip (same as extract_topics.py)
        self.skip_url_patterns = [
            'opensearch.xml',
            'robots.txt',
            'sitemap.xml',
            'manifest.json',
            '.js',
            '.css',
            '.png',
            '.jpg',
            '.jpeg',
            '.gif',
            '.svg',
            '.ico',
            '.woff',
            '.woff2',
            '.ttf',
            '.eot',
            '.pdf',
            '.zip',
            '.tar',
            '.gz',
            '/search',
            '/search/',
            '/api/',
            '/_next/',
            '/assets/js/',
            '/assets/css/',
            '/static/js/',
            '/static/css/',
        ]

        # BFS queue and tracking sets
        self.queue = deque([start_url])
        self.visited = set()
        self.to_visit = {start_url}

        # Results tracking
        self.successful = []
        self.failed = []
        self.crawl_data = {}

        # Create output directory
        self.output_dir.mkdir(exist_ok=True)

        print(f"🕷️  BFS Crawler initialized")
        print(f"   Start URL: {start_url}")
        print(f"   Domain: {self.start_domain}")
        print(f"   Max pages: {max_pages}")
        print(f"   Same domain only: {same_domain_only}")
        print(f"   Extract topics: {extract_topics}")

    def should_skip_url(self, url: str) -> bool:
        """
        Check if URL should be skipped (non-content files)

        Args:
            url: URL to check

        Returns:
            True if should skip, False otherwise
        """
        url_lower = url.lower()
        for pattern in self.skip_url_patterns:
            if pattern in url_lower:
                return True
        return False

    def extract_links(self, html: str, base_url: str) -> Set[str]:
        """
        Extract all links from HTML content

        Args:
            html: HTML content
            base_url: Base URL for resolving relative links

        Returns:
            Set of absolute URLs
        """
        links = set()

        # Find all href attributes
        href_pattern = r'href=["\']([^"\']+)["\']'
        matches = re.findall(href_pattern, html)

        for match in matches:
            # Skip anchors, javascript, mailto, etc.
            if match.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue

            # Convert to absolute URL
            try:
                absolute_url = urljoin(base_url, match)

                # Remove fragment
                absolute_url = absolute_url.split('#')[0]

                # Check domain if same_domain_only
                if self.same_domain_only:
                    url_domain = urlparse(absolute_url).netloc
                    if url_domain != self.start_domain:
                        continue

                # Skip non-content URLs (JS, CSS, images, etc.)
                if self.should_skip_url(absolute_url):
                    continue

                links.add(absolute_url)
            except:
                continue

        return links

    async def crawl_page(self, url: str, level: int) -> Dict:
        """
        Crawl a single page

        Args:
            url: URL to crawl
            level: BFS level (depth from start)

        Returns:
            Dictionary with crawl results
        """
        result = {
            'url': url,
            'level': level,
            'success': False,
            'markdown': None,
            'html': None,
            'links_found': 0,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }

        try:
            # Configure browser
            browser_config = BrowserConfig(headless=True, verbose=False)

            # Crawl with extended timeout and proper JavaScript rendering
            async with AsyncWebCrawler(config=browser_config) as crawler:
                crawl_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    page_timeout=120000,        # 120 seconds instead of default 60
                    wait_until="networkidle",   # Wait for network to be idle (better for JS-heavy sites)
                    delay_before_return_html=2.0  # Wait 2s for JavaScript to render
                )
                crawl_result = await crawler.arun(url=url, config=crawl_config)

                if crawl_result.success:
                    result['success'] = True
                    result['markdown'] = crawl_result.markdown
                    result['html'] = crawl_result.html

                    # Extract links from HTML
                    if crawl_result.html:
                        links = self.extract_links(crawl_result.html, url)
                        result['links'] = list(links)
                        result['links_found'] = len(links)
                    else:
                        result['links'] = []
                else:
                    result['error'] = getattr(crawl_result, 'error_message', 'Unknown error')

        except Exception as e:
            result['error'] = str(e)

        return result

    async def crawl_bfs(self):
        """
        Main BFS crawling logic

        Crawls pages level by level (breadth-first)
        """
        print(f"\n🚀 Starting BFS crawl...")
        print(f"{'='*80}\n")

        level = 0
        pages_crawled = 0

        while self.queue and pages_crawled < self.max_pages:
            # Get next URL from queue
            url = self.queue.popleft()

            # Skip if already visited
            if url in self.visited:
                continue

            # Mark as visited
            self.visited.add(url)
            pages_crawled += 1

            # Determine level (approximate based on pages crawled)
            if pages_crawled == 1:
                level = 0
            elif pages_crawled <= 10:
                level = 1
            elif pages_crawled <= 30:
                level = 2
            else:
                level = 3

            # Print progress
            print(f"[{pages_crawled}/{self.max_pages}] Level {level}: {url}")

            # Crawl page
            result = await self.crawl_page(url, level)

            # Save result
            self.crawl_data[url] = result

            if result['success']:
                print(f"  ✅ Success! Found {result['links_found']} links")
                print(f"     Content: {len(result['markdown'])} chars")
                self.successful.append(url)

                # Add discovered links to queue
                links_added = 0
                for link in result.get('links', []):
                    if link not in self.visited and link not in self.to_visit:
                        self.queue.append(link)
                        self.to_visit.add(link)
                        links_added += 1

                if links_added > 0:
                    print(f"     Added {links_added} new links to queue (Queue size: {len(self.queue)})")

                # Save page
                self.save_page(url, result)

            else:
                print(f"  ❌ Failed: {result['error']}")
                self.failed.append(url)

            # Brief pause between pages
            await asyncio.sleep(0.5)

        print(f"\n{'='*80}")
        print(f"✅ BFS crawl complete!")
        print(f"   Pages crawled: {pages_crawled}")
        print(f"   Successful: {len(self.successful)}")
        print(f"   Failed: {len(self.failed)}")
        print(f"   Links discovered: {len(self.to_visit)}")

    def save_page(self, url: str, result: Dict):
        """
        Save crawled page as markdown file

        Args:
            url: Page URL
            result: Crawl result
        """
        if not result['success'] or not result['markdown']:
            return

        # Create filename from URL
        filename = url.replace('https://', '').replace('http://', '')
        filename = filename.replace('/', '_').replace('?', '_').replace('&', '_')
        filename = filename[:150] + '.md'

        filepath = self.output_dir / filename

        # Write markdown file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {url}\n\n")
            f.write(f"**Crawled**: {result['timestamp']}\n")
            f.write(f"**Level**: {result['level']}\n")
            f.write(f"**Links found**: {result['links_found']}\n\n")
            f.write("---\n\n")
            f.write(result['markdown'])

    def generate_report(self) -> str:
        """
        Generate detailed crawl report

        Returns:
            Report as string
        """
        report = []
        report.append("=" * 80)
        report.append("📊 BFS CRAWL REPORT")
        report.append("=" * 80)
        report.append("")

        # Summary
        report.append("## Summary")
        report.append(f"  Start URL: {self.start_url}")
        report.append(f"  Domain: {self.start_domain}")
        report.append(f"  Total pages visited: {len(self.visited)}")
        report.append(f"  Successful: {len(self.successful)}")
        report.append(f"  Failed: {len(self.failed)}")
        report.append(f"  Links discovered: {len(self.to_visit)}")
        report.append(f"  Pages saved: {len(self.successful)}")
        report.append("")

        # Pages by level
        levels = {}
        for url, data in self.crawl_data.items():
            level = data.get('level', 0)
            if level not in levels:
                levels[level] = []
            levels[level].append(url)

        report.append("## Pages by Level")
        for level in sorted(levels.keys()):
            report.append(f"  Level {level}: {len(levels[level])} pages")
        report.append("")

        # Successful pages
        report.append("## Successful Pages")
        for i, url in enumerate(self.successful, 1):
            data = self.crawl_data[url]
            report.append(f"  {i}. {url}")
            report.append(f"     Level: {data['level']} | Links: {data['links_found']} | Size: {len(data['markdown'])} chars")
        report.append("")

        # Failed pages
        if self.failed:
            report.append("## Failed Pages")
            for i, url in enumerate(self.failed, 1):
                data = self.crawl_data.get(url, {})
                error = data.get('error', 'Unknown error')
                report.append(f"  {i}. {url}")
                report.append(f"     Error: {error}")
            report.append("")

        # Link graph (top 10 pages by links found)
        report.append("## Top Pages by Links Found")
        sorted_pages = sorted(
            [(url, data.get('links_found', 0)) for url, data in self.crawl_data.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        for i, (url, links) in enumerate(sorted_pages, 1):
            report.append(f"  {i}. {url} ({links} links)")
        report.append("")

        # Output files
        report.append("## Output")
        report.append(f"  Directory: {self.output_dir}/")
        report.append(f"  Markdown files: {len(self.successful)}")
        report.append(f"  Report: {self.output_dir}/crawl_report.txt")
        report.append(f"  Data: {self.output_dir}/crawl_data.json")
        report.append("")

        report.append("=" * 80)
        report.append("✅ Report generated: " + datetime.now().isoformat())
        report.append("=" * 80)

        return "\n".join(report)

    def save_report(self):
        """Save report and data to files"""
        # Save text report
        report = self.generate_report()
        report_file = self.output_dir / "crawl_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📄 Report saved: {report_file}")

        # Save JSON data
        data_file = self.output_dir / "crawl_data.json"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump({
                'start_url': self.start_url,
                'start_domain': self.start_domain,
                'total_visited': len(self.visited),
                'successful': self.successful,
                'failed': self.failed,
                'crawl_data': self.crawl_data
            }, f, indent=2)
        print(f"📄 Data saved: {data_file}")


async def main():
    """Example usage"""
    print("=" * 80)
    print("🕷️  BFS Web Crawler with Topic Extraction")
    print("=" * 80)

    # Configuration
    start_url = "https://docs.python.org/3/tutorial/"
    max_pages = 5  # Limit for testing (save cost and time)

    # Create crawler
    crawler = BFSCrawler(
        start_url=start_url,
        max_pages=max_pages,
        same_domain_only=True,
        output_dir="bfs_crawled",
        extract_topics=True  # Automatically extract topics after crawling
    )

    # Run BFS crawl
    await crawler.crawl_bfs()

    # Generate and save crawl report
    crawler.save_report()

    # Print crawl report to console
    print("\n" + crawler.generate_report())

    # Run topic extraction if enabled
    if crawler.extract_topics:
        print("\n" + "="*80)
        print("🔍 Starting Topic Extraction Phase...")
        print("="*80)

        if not TOPIC_EXTRACTION_AVAILABLE:
            print("❌ Topic extraction not available (extract_topics.py not found)")
            return

        if not os.getenv('GEMINI_API_KEY'):
            print("❌ GEMINI_API_KEY not set. Skipping topic extraction.")
            return

        try:
            # Initialize topic extractor
            extractor = TopicExtractor()

            # Extract topics from all crawled files
            all_topics = await extractor.extract_from_crawled_files(str(crawler.output_dir))

            if not all_topics:
                print("\n⚠️  No topics extracted. Make sure crawled files exist.")
                return

            # Generate and save topic report
            extractor.save_report(all_topics, f"{crawler.output_dir}/topics_report.txt")

            # Print summary
            print("\n" + "="*80)
            print("✅ Complete Workflow Finished!")
            print("="*80)
            print(f"📊 Crawling Summary:")
            print(f"   Pages crawled: {len(crawler.successful)}")
            print(f"   Links discovered: {len(crawler.to_visit)}")
            print(f"\n🔍 Extraction Summary:")
            print(f"   URLs processed: {len(all_topics)}")
            print(f"   Total topics: {sum(len(topics) for topics in all_topics.values())}")
            print(f"\n📁 Output:")
            print(f"   Crawl report: {crawler.output_dir}/crawl_report.txt")
            print(f"   Topics report: {crawler.output_dir}/topics_report.txt")
            print(f"   Topics JSON: {crawler.output_dir}/topics_report.json")
            print("="*80)

        except Exception as e:
            print(f"\n❌ Topic extraction failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
