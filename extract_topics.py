#!/usr/bin/env python3
"""
Topic Extractor

Extracts topics from crawled markdown content using LLM.
Creates a single report file showing topics from each URL.
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Suppress gRPC warnings (must be set BEFORE importing genai)
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

import google.generativeai as genai
from utils.rate_limiter import get_llm_rate_limiter

load_dotenv()


class TopicExtractor:
    """
    Simple topic extractor using Gemini LLM
    """

    def __init__(self, api_key: str = None):
        """
        Initialize topic extractor

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Please set it in .env file")

        genai.configure(api_key=self.api_key)
        # Using gemini-2.5-flash-lite - cheapest option
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')

        # Rate limiter
        self.llm_limiter = get_llm_rate_limiter()

        print("✅ Topic extractor initialized")

    def create_extraction_prompt(self, markdown_content: str, url: str) -> str:
        """
        Create an improved prompt for high-quality topic extraction

        Args:
            markdown_content: Page content in markdown
            url: Source URL

        Returns:
            Prompt string
        """
        prompt = f"""Extract HIGH-QUALITY, DISTINCT topics from this web page content.

URL: {url}

Content:
{markdown_content[:16000]}

CRITICAL EXTRACTION STRATEGY:

**IF the page contains a chapter/section structure (table of contents, numbered sections, topic list):**
   - Extract topics FROM the chapter/section titles and their content
   - Focus on what each chapter/section TEACHES
   - Example: If you see "4.1 If Statements", "4.2 For Loops", extract those specific concepts

**IF the page contains tutorial/guide content:**
   - Extract the specific programming concepts being taught
   - Focus on actionable, educational content

**IGNORE all introduction text, navigation, and meta-information**

CRITICAL QUALITY REQUIREMENTS:

1. **Extract ONLY Topics That TEACH Programming/Technical Concepts**:
   - Topics must TEACH specific programming concepts, syntax, or techniques
   - Topics must contain CODE EXAMPLES, technical explanations, or how-to instructions
   - Focus on EDUCATIONAL CONTENT that helps users learn or solve problems

   ❌ NEVER extract:
   - Meta-information (e.g., "Target Audience", "About This Tutorial", "Who Should Read")
   - Navigation/UI (e.g., "Index", "Table of Contents", "Menu", "Search")
   - Documentation structure (e.g., "Tutorial Organization", "How to Use This Guide")
   - Version/language selection (e.g., "Documentation Versions", "Language Options")
   - Generic descriptions (e.g., "Python is easy to learn" WITHOUT teaching specific concepts)
   - Introductory overview text (e.g., "Python Fundamentals Overview" WITHOUT specific concepts)

   ✅ ALWAYS extract:
   - Programming syntax (e.g., "Python If-Else Statements", "For Loop Syntax")
   - Data structures (e.g., "Python Lists Operations", "Dictionary Methods")
   - Programming techniques (e.g., "Exception Handling with Try-Except", "File I/O")
   - APIs and modules (e.g., "Using the os Module", "String Methods")
   - Code patterns and best practices (e.g., "List Comprehensions", "Context Managers")

2. **Ensure Topics Are DISTINCT and NON-OVERLAPPING**:
   - Each topic must cover DIFFERENT information
   - NO duplicate or highly similar topics
   - NO topics that are subsets of other topics
   - Topics should be clearly separable from each other
   - If two topics seem similar, combine them into ONE comprehensive topic

3. **Quality Standards**:
   - Extract 2-4 topics ONLY (prefer quality over quantity)
   - Each topic must be SUBSTANTIAL (not trivial)
   - Title: Clear, specific, descriptive (5-8 words)
   - Category: One word - tutorial, guide, reference, concept, documentation, api, troubleshooting
   - Summary: 2-3 sentences explaining WHAT this topic covers and WHY it matters (150-250 chars)
   - Description: Key details and context (300-800 chars - be concise!)

4. **Description Requirements**:
   - Focus on KEY information: concepts, syntax, common patterns
   - Include 1-2 code examples if relevant (keep them SHORT)
   - Mention important warnings or gotchas
   - BE CONCISE - descriptions should be 300-800 characters, NOT pages of text

5. **Output Format**:
[
  {{
    "title": "Specific Descriptive Topic Title",
    "category": "category",
    "summary": "Clear summary explaining what this topic covers and why it's useful...",
    "description": "COMPREHENSIVE content with ALL details, examples, code snippets, explanations, warnings, best practices, and step-by-step instructions..."
  }}
]

EXAMPLES OF GOOD vs BAD TOPICS:

❌ BAD: "Python Tutorial Introduction" - too vague
✅ GOOD: "Python If-Else Conditional Statements"

❌ BAD: "Navigation Menu" - not substantive content
✅ GOOD: "Python Exception Handling with Try-Except"

❌ BAD: Two topics: "Python Lists Basics" and "Python Lists Operations" - should be ONE topic
✅ GOOD: One topic: "Python Lists - Creation, Indexing, and Operations"

Return ONLY the JSON array with 2-4 HIGH-QUALITY, DISTINCT topics:"""

        return prompt

    def validate_topic_quality(self, topic: dict) -> tuple[bool, str]:
        """
        Validate if a topic meets quality standards

        Args:
            topic: Topic dictionary

        Returns:
            (is_valid, reason) tuple
        """
        title = topic.get('title', '').lower()
        summary = topic.get('summary', '')
        description = topic.get('description', '')

        # List of non-substantive keywords that indicate low-quality topics
        non_substantive_keywords = [
            # Navigation/UI
            'navigation', 'menu', 'index', 'table of contents', 'sidebar',
            'header', 'footer', 'theme', 'layout', 'page structure',
            'links', 'search', 'home page', 'quick search',
            'general index', 'module index',

            # Meta-information
            'about this', 'target audience', 'intended for', 'designed for',
            'who should read', 'prerequisite', 'audience',
            'tutorial structure', 'how to use', 'documentation guide',

            # Version/Language selection
            'version', 'versioning', 'language selection', 'language options',
            'translation', 'multilingual', 'available languages',

            # Legal/Administrative
            'copyright', 'license', 'terms of use', 'privacy policy'
        ]

        # Check for non-substantive topics
        for keyword in non_substantive_keywords:
            if keyword in title:
                return False, f"Non-substantive topic: contains '{keyword}'"

        # Check minimum content length
        if len(description) < 100:
            return False, "Description too short (< 100 chars)"

        if len(summary) < 30:
            return False, "Summary too short (< 30 chars)"

        # Check for vague/generic titles without specific content
        vague_only_titles = ['introduction', 'overview', 'about', 'general']
        if title in vague_only_titles:
            return False, f"Too vague: '{title}'"

        # Check title length (should be descriptive, not too short)
        title_words = topic.get('title', '').split()
        if len(title_words) < 2:
            return False, "Title too short (< 2 words)"

        if len(title_words) > 12:
            return False, "Title too long (> 12 words)"

        return True, "Valid"

    def create_topic_embedding(self, topic: dict) -> list:
        """
        Create embedding for a topic using Gemini
        Uses title + summary for richer semantic representation

        Title provides key concepts and keywords
        Summary provides context and detailed meaning
        Together they give the best semantic signal for similarity comparison

        Args:
            topic: Topic dictionary

        Returns:
            Embedding vector (768-dim)
        """
        # Combine title and summary for comprehensive semantic representation
        # Title: Key concepts and keywords
        # Summary: Context and detailed meaning
        title = topic.get('title', '')
        summary = topic.get('summary', '')

        # Combine with natural separation
        text = f"{title}. {summary}" if title and summary else (title or summary)

        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="semantic_similarity"  # Optimized for similarity comparison
            )
            return result['embedding']
        except Exception as e:
            print(f"  ⚠️  Embedding error for '{topic.get('title', 'unknown')}': {e}")
            return None

    def calculate_cosine_similarity(self, embedding1: list, embedding2: list) -> float:
        """
        Calculate cosine similarity between two embeddings

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0-1)
        """
        if not embedding1 or not embedding2:
            return 0.0

        import math

        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = math.sqrt(sum(a * a for a in embedding1))
        magnitude2 = math.sqrt(sum(b * b for b in embedding2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        similarity = dot_product / (magnitude1 * magnitude2)
        return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]

    def check_topic_similarity(self, topic1: dict, topic2: dict) -> float:
        """
        Calculate semantic similarity between two topics using Gemini embeddings
        Much better than word overlap - captures actual meaning!

        Args:
            topic1: First topic
            topic2: Second topic

        Returns:
            Similarity score (0-1)
        """
        # Create embeddings for both topics
        embedding1 = self.create_topic_embedding(topic1)
        embedding2 = self.create_topic_embedding(topic2)

        if not embedding1 or not embedding2:
            # Fallback to simple word overlap if embeddings fail
            def get_words(text):
                return set(text.lower().split())

            title1_words = get_words(topic1.get('title', ''))
            title2_words = get_words(topic2.get('title', ''))
            summary1_words = get_words(topic1.get('summary', ''))
            summary2_words = get_words(topic2.get('summary', ''))

            # Calculate word overlap
            title_overlap = len(title1_words & title2_words) / max(len(title1_words | title2_words), 1)
            summary_overlap = len(summary1_words & summary2_words) / max(len(summary1_words | summary2_words), 1)

            # Weighted average
            return 0.6 * title_overlap + 0.4 * summary_overlap

        # Calculate cosine similarity between embeddings
        similarity = self.calculate_cosine_similarity(embedding1, embedding2)
        return similarity

    def merge_similar_topics(self, topic1: dict, topic2: dict) -> dict:
        """
        Merge two similar topics into one comprehensive topic

        Args:
            topic1: First topic (will be the base)
            topic2: Second topic (will be merged into first)

        Returns:
            Merged topic dictionary
        """
        # Use the longer, more descriptive title
        title1 = topic1.get('title', '')
        title2 = topic2.get('title', '')
        merged_title = title1 if len(title1) >= len(title2) else title2

        # Combine summaries (avoid exact duplicates)
        summary1 = topic1.get('summary', '')
        summary2 = topic2.get('summary', '')

        if summary1.lower() == summary2.lower():
            merged_summary = summary1
        else:
            merged_summary = f"{summary1} {summary2}".strip()

        # Combine descriptions (keep all unique information)
        desc1 = topic1.get('description', '')
        desc2 = topic2.get('description', '')

        # Simple merge: combine both descriptions with a separator
        # The LLM will handle the combined content later
        if desc1 and desc2:
            merged_description = f"{desc1}\n\n{desc2}"
        else:
            merged_description = desc1 or desc2

        # Use the first topic's category (or the more specific one)
        merged_category = topic1.get('category', topic2.get('category', 'general'))

        return {
            'title': merged_title,
            'category': merged_category,
            'summary': merged_summary,
            'description': merged_description
        }

    def deduplicate_topics(self, topics: list) -> list:
        """
        Merge duplicate or highly similar topics instead of removing them

        Args:
            topics: List of topic dictionaries

        Returns:
            Deduplicated and merged list of topics
        """
        if len(topics) <= 1:
            return topics

        # Similarity threshold for considering topics as duplicates
        # Using Gemini embeddings, which give semantic similarity (0-1)
        # Since topics from same page share context, baseline similarity is high
        # 0.85+ = Very similar / duplicates (merge)
        # 0.75-0.85 = Similar but distinct (keep separate)
        # <0.75 = Different topics (definitely keep separate)
        SIMILARITY_THRESHOLD = 0.85

        deduplicated = []

        for topic in topics:
            merged = False

            for i, existing in enumerate(deduplicated):
                similarity = self.check_topic_similarity(topic, existing)

                if similarity > SIMILARITY_THRESHOLD:
                    # Merge instead of remove
                    print(f"  🔀 Merging similar topics: '{topic['title']}' + '{existing['title']}' (similarity: {similarity:.2f})")
                    merged_topic = self.merge_similar_topics(existing, topic)
                    deduplicated[i] = merged_topic
                    merged = True
                    break

            if not merged:
                deduplicated.append(topic)

        return deduplicated

    async def extract_topics_from_text(self, markdown_content: str, url: str, retry_count: int = 0) -> list:
        """
        Extract topics from markdown content

        Args:
            markdown_content: Markdown content
            url: Source URL
            retry_count: Current retry attempt

        Returns:
            List of topics [{'title': ..., 'category': ..., 'summary': ...}]
        """
        print(f"  🔍 Extracting topics from: {url[:50]}...")

        try:
            # Create prompt with more content for comprehensive extraction
            prompt = self.create_extraction_prompt(markdown_content, url)

            # Call Gemini with temperature to reduce randomness
            self.llm_limiter.wait_if_needed()
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Lower temperature for more consistent output
                )
            )
            response_text = response.text.strip()

            # Parse JSON
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                # Split by ``` and take the middle part
                parts = response_text.split('```')
                if len(parts) >= 2:
                    response_text = parts[1]
                    # Remove 'json' prefix if present
                    if response_text.strip().startswith('json'):
                        response_text = response_text.strip()[4:]

            response_text = response_text.strip()

            # Try to find JSON array in response
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']')

            if start_idx != -1 and end_idx != -1:
                response_text = response_text[start_idx:end_idx+1]

            # Parse JSON
            topics = json.loads(response_text)

            # Validate topics structure
            if not isinstance(topics, list):
                raise ValueError("Response is not a list")

            # Filter and validate topics
            valid_topics = []
            rejected_count = 0

            for topic in topics:
                # Check basic structure
                if not isinstance(topic, dict) or 'title' not in topic or 'category' not in topic:
                    print(f"  ⚠️  Skipping malformed topic")
                    rejected_count += 1
                    continue

                # Validate quality
                is_valid, reason = self.validate_topic_quality(topic)

                if is_valid:
                    valid_topics.append(topic)
                else:
                    print(f"  ❌ Rejected: '{topic['title']}' - {reason}")
                    rejected_count += 1

            # Deduplicate and merge topics
            if len(valid_topics) > 1:
                print(f"  🔍 Checking for similar topics to merge...")
                before_count = len(valid_topics)
                deduplicated = self.deduplicate_topics(valid_topics)
                after_count = len(deduplicated)
                merged_count = before_count - after_count

                if merged_count > 0:
                    print(f"  ✅ Merged {merged_count} similar topic(s) to preserve information")

                valid_topics = deduplicated

            if valid_topics:
                summary_msg = f"  ✅ Extracted {len(valid_topics)} high-quality topics"
                if rejected_count > 0:
                    summary_msg += f" ({rejected_count} rejected)"
                print(summary_msg)
                return valid_topics
            else:
                raise ValueError(f"No valid topics found in response ({rejected_count} topics rejected for quality issues)")

        except json.JSONDecodeError as e:
            print(f"  ❌ JSON parse error: {e}")
            print(f"  Response was: {response_text[:500] if 'response_text' in locals() else 'No response'}")

            # Retry once with smaller content
            if retry_count == 0:
                print(f"  🔄 Retrying with smaller content...")
                return await self.extract_topics_from_text(markdown_content[:3000], url, retry_count=1)

            return []
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return []

    async def extract_from_crawled_files(self, crawl_dir: str = "bfs_crawled") -> dict:
        """
        Extract topics from ONLY the files crawled in the current session
        (reads from crawl_data.json to get the list of successfully crawled URLs)

        Args:
            crawl_dir: Directory containing crawled files

        Returns:
            Dictionary mapping URL to topics
        """
        crawl_path = Path(crawl_dir)

        if not crawl_path.exists():
            print(f"❌ Directory not found: {crawl_dir}")
            return {}

        # Read crawl_data.json to get list of successfully crawled URLs
        crawl_data_file = crawl_path / "crawl_data.json"

        if not crawl_data_file.exists():
            print(f"❌ crawl_data.json not found in {crawl_dir}")
            print("   Run the crawler first to generate crawl data")
            return {}

        try:
            with open(crawl_data_file, 'r', encoding='utf-8') as f:
                crawl_data = json.load(f)
        except Exception as e:
            print(f"❌ Error reading crawl_data.json: {e}")
            return {}

        # Get list of successfully crawled URLs
        successful_urls = crawl_data.get('successful', [])

        if not successful_urls:
            print(f"❌ No successful URLs found in crawl_data.json")
            return {}

        print(f"\n📚 Crawl session info:")
        print(f"   Start URL: {crawl_data.get('start_url', 'N/A')}")
        print(f"   Total visited: {crawl_data.get('total_visited', 0)}")
        print(f"   Successful: {len(successful_urls)}")
        print("=" * 80)
        print(f"\n📄 Will extract topics from {len(successful_urls)} crawled documents:")
        for url in successful_urls:
            print(f"   • {url}")
        print("=" * 80)

        all_topics = {}

        # Process each successfully crawled URL
        for i, url in enumerate(successful_urls, 1):
            print(f"\n[{i}/{len(successful_urls)}] Processing: {url}")

            # Get the crawl data for this URL
            url_data = crawl_data.get('crawl_data', {}).get(url, {})

            if not url_data.get('success'):
                print(f"  ⚠️  Skipping: marked as failed in crawl_data")
                continue

            # Get markdown content directly from crawl_data
            markdown_content = url_data.get('markdown', '')

            if not markdown_content:
                print(f"  ⚠️  Skipping: no markdown content in crawl_data")
                continue

            # Extract topics
            topics = await self.extract_topics_from_text(markdown_content, url)

            if topics:
                all_topics[url] = topics

            # Brief pause to avoid rate limiting
            await asyncio.sleep(1)

        # CROSS-PAGE DEDUPLICATION
        # After extracting from all pages, check for duplicate topics across different URLs
        if len(all_topics) > 1:
            print("\n" + "=" * 80)
            print("🔍 Cross-Page Deduplication")
            print("=" * 80)
            print("Checking for similar topics across different pages...")

            # Collect all topics with their source URLs
            all_topics_with_urls = []
            for url, topics in all_topics.items():
                for topic in topics:
                    all_topics_with_urls.append({'topic': topic, 'url': url})

            before_count = len(all_topics_with_urls)

            # Deduplicate across all pages
            deduplicated_with_urls = []
            for item in all_topics_with_urls:
                topic = item['topic']
                url = item['url']
                merged = False

                for i, existing_item in enumerate(deduplicated_with_urls):
                    existing_topic = existing_item['topic']
                    similarity = self.check_topic_similarity(topic, existing_topic)

                    if similarity > 0.85:  # Same threshold as within-page dedup
                        print(f"  🔀 Merging cross-page topics (similarity: {similarity:.2f}):")
                        print(f"     '{existing_topic['title']}' (from {existing_item['url']})")
                        print(f"     '{topic['title']}' (from {url})")

                        merged_topic = self.merge_similar_topics(existing_topic, topic)
                        deduplicated_with_urls[i] = {'topic': merged_topic, 'url': existing_item['url']}
                        merged = True
                        break

                if not merged:
                    deduplicated_with_urls.append(item)

            after_count = len(deduplicated_with_urls)
            merged_count = before_count - after_count

            if merged_count > 0:
                print(f"\n✅ Merged {merged_count} cross-page duplicate(s)")

                # Rebuild all_topics dictionary with deduplicated topics
                all_topics = {}
                for item in deduplicated_with_urls:
                    url = item['url']
                    topic = item['topic']
                    if url not in all_topics:
                        all_topics[url] = []
                    all_topics[url].append(topic)
            else:
                print(f"\n✅ No cross-page duplicates found")

        print("\n" + "=" * 80)
        print(f"✅ Extraction complete!")
        print(f"   URLs from crawl: {len(successful_urls)}")
        print(f"   URLs with topics: {len(all_topics)}")
        print(f"   Total topics: {sum(len(topics) for topics in all_topics.values())}")

        return all_topics

    def generate_topics_report(self, all_topics: dict) -> str:
        """
        Generate a single report file showing all topics

        Args:
            all_topics: Dictionary mapping URL to topics

        Returns:
            Report as string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("📚 TOPICS EXTRACTION REPORT")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total URLs: {len(all_topics)}")
        lines.append(f"Total Topics: {sum(len(topics) for topics in all_topics.values())}")
        lines.append("")
        lines.append("=" * 80)
        lines.append("")

        # Group topics by URL
        for i, (url, topics) in enumerate(all_topics.items(), 1):
            lines.append(f"\n## [{i}] {url}")
            lines.append(f"Topics found: {len(topics)}")
            lines.append("-" * 80)

            for j, topic in enumerate(topics, 1):
                lines.append(f"\n### {j}. {topic.get('title', 'Untitled')}")
                lines.append(f"**Category**: {topic.get('category', 'general')}")
                lines.append(f"**Summary**: {topic.get('summary', 'No summary')}")

                # Add description if available
                if 'description' in topic and topic['description']:
                    lines.append(f"**Description**: {topic.get('description', '')}")

            lines.append("\n" + "=" * 80)

        # Summary by category
        lines.append("\n\n📊 TOPICS BY CATEGORY")
        lines.append("=" * 80)

        categories = {}
        for topics in all_topics.values():
            for topic in topics:
                cat = topic.get('category', 'general')
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(topic.get('title', 'Untitled'))

        for category in sorted(categories.keys()):
            lines.append(f"\n**{category.upper()}** ({len(categories[category])} topics)")
            for title in categories[category]:
                lines.append(f"  - {title}")

        lines.append("\n" + "=" * 80)
        lines.append("✅ Report complete!")
        lines.append("=" * 80)

        return "\n".join(lines)

    def save_report(self, all_topics: dict, output_file: str = "bfs_crawled/topics_report.txt"):
        """
        Save topics report to file

        Args:
            all_topics: Dictionary of topics
            output_file: Output file path
        """
        report = self.generate_topics_report(all_topics)

        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n📄 Topics report saved: {output_path}")

        # Also save JSON
        json_file = output_path.with_suffix('.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(all_topics, f, indent=2)

        print(f"📄 Topics JSON saved: {json_file}")


async def main():
    """Main function"""
    print("=" * 80)
    print("🔍 Topic Extraction from Crawled Content")
    print("=" * 80)

    # Initialize extractor
    try:
        extractor = TopicExtractor()
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease add GEMINI_API_KEY to your .env file:")
        print("  GEMINI_API_KEY=your-api-key-here")
        return

    # Extract topics from all crawled files
    all_topics = await extractor.extract_from_crawled_files("bfs_crawled")

    if not all_topics:
        print("\n⚠️  No topics extracted. Make sure you have crawled files in bfs_crawled/")
        return

    # Generate and save report
    extractor.save_report(all_topics)

    # Print report to console
    print("\n" + extractor.generate_topics_report(all_topics))


if __name__ == "__main__":
    asyncio.run(main())
