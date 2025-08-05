import asyncio
import json
import os
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from dotenv import load_dotenv
from models.schemas import ResultSchema

# Import the DifyAPI class
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Test_dify import DifyAPI


class CrawlWorkflow:
    def __init__(self, dify_base_url="http://localhost:8088", dify_api_key=None, gemini_api_key=None):
        """Initialize the crawl workflow with API configurations."""
        self.dify_api = DifyAPI(base_url=dify_base_url, api_key=dify_api_key)
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        self.knowledge_bases = {}  # Cache of existing knowledge bases
        self.tags_cache = {}  # Cache of existing tags
        self._initialized = False  # Track initialization state
        
    async def initialize(self):
        """Initialize workflow by fetching existing knowledge bases and tags."""
        try:
            # Get existing knowledge bases
            response = self.dify_api.get_knowledge_base_list()
            if response.status_code == 200:
                kb_data = response.json()
                print(f"Debug: Knowledge bases response: {kb_data}")
                
                # Handle different possible response structures
                kb_list = []
                if isinstance(kb_data, dict):
                    if 'data' in kb_data:
                        kb_list = kb_data['data']
                    elif 'datasets' in kb_data:
                        kb_list = kb_data['datasets']
                    elif isinstance(kb_data.get('data'), list):
                        kb_list = kb_data['data']
                elif isinstance(kb_data, list):
                    kb_list = kb_data
                
                # Process knowledge bases with proper error handling
                for kb in kb_list:
                    try:
                        if isinstance(kb, dict):
                            # Try different possible field names
                            kb_name = kb.get('name') or kb.get('title') or kb.get('dataset_name')
                            kb_id = kb.get('id') or kb.get('dataset_id') or kb.get('uuid')
                            
                            if kb_name and kb_id:
                                self.knowledge_bases[kb_name] = kb_id
                                print(f"  ✅ Found existing knowledge base: {kb_name} (ID: {kb_id})")
                            else:
                                print(f"  ⚠️  Skipping knowledge base with incomplete data: {kb}")
                    except Exception as kb_error:
                        print(f"  ⚠️  Error processing knowledge base entry: {kb_error}")
                        continue
            else:
                print(f"Failed to get knowledge bases: {response.status_code} - {response.text}")
            
            # Get existing tags
            response = self.dify_api.get_knowledge_base_type_tags()
            if response.status_code == 200:
                tags_data = response.json()
                print(f"Debug: Tags response: {tags_data}")
                
                # Handle different possible response structures for tags
                tag_list = []
                if isinstance(tags_data, dict):
                    if 'data' in tags_data:
                        tag_list = tags_data['data']
                    elif 'tags' in tags_data:
                        tag_list = tags_data['tags']
                elif isinstance(tags_data, list):
                    tag_list = tags_data
                
                for tag in tag_list:
                    try:
                        if isinstance(tag, dict):
                            tag_name = tag.get('name') or tag.get('title')
                            tag_id = tag.get('id') or tag.get('tag_id') or tag.get('uuid')
                            
                            if tag_name and tag_id:
                                self.tags_cache[tag_name] = tag_id
                                print(f"  ✅ Found existing tag: {tag_name} (ID: {tag_id})")
                    except Exception as tag_error:
                        print(f"  ⚠️  Error processing tag entry: {tag_error}")
                        continue
            else:
                print(f"Failed to get tags: {response.status_code} - {response.text}")
                        
        except Exception as e:
            print(f"Warning: Could not initialize existing data: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._initialized = True
            print(f"📊 Initialization complete: {len(self.knowledge_bases)} knowledge bases, {len(self.tags_cache)} tags cached")
    
    async def refresh_cache(self):
        """Force refresh of knowledge bases and tags cache from API."""
        print("🔄 Refreshing cache from API...")
        self.knowledge_bases.clear()
        self.tags_cache.clear()
        await self.initialize()
    
    def categorize_content(self, content: str, url: str) -> Tuple[str, List[str]]:
        """Analyze content and determine category and appropriate tags - optimized for token efficiency."""
        domain = urlparse(url).netloc.lower()
        
        # Simple categorization based on domain and content keywords
        category = "general"
        tags = []
        
        # Domain-based categorization
        if 'news' in domain or 'blog' in domain:
            category = "news_and_blogs"
            tags.append("news")
        elif 'doc' in domain or 'wiki' in domain:
            category = "documentation"
            tags.append("documentation")
        elif 'edu' in domain or 'university' in domain:
            category = "education"
            tags.append("education")
        elif 'github' in domain or 'gitlab' in domain:
            category = "development"
            tags.append("code")
        elif 'api' in domain:
            category = "api_documentation" 
            tags.append("api")
        
        # Content-based tagging - check only first 500 chars for efficiency
        content_sample = content[:500].lower() if len(content) > 500 else content.lower()
        
        # Technology tags
        if any(tech in content_sample for tech in ['python', 'javascript', 'java', 'react', 'node']):
            tags.append("programming")
        if any(tech in content_sample for tech in ['blockchain', 'crypto', 'bitcoin', 'ethereum']):
            tags.append("blockchain")
        if any(tech in content_sample for tech in ['ai', 'machine learning', 'artificial intelligence', 'ml']):
            tags.append("ai")
        if any(tech in content_sample for tech in ['api', 'rest', 'graphql', 'endpoint']):
            tags.append("api")
        
        # Business/Finance tags
        if any(term in content_sample for term in ['business', 'finance', 'economy', 'market']):
            tags.append("business")
        if any(term in content_sample for term in ['tutorial', 'guide', 'how to', 'step by step']):
            tags.append("tutorial")
        
        # Remove duplicates and add domain tag
        tags = list(set(tags))
        tags.append(domain.replace('.', '_'))
        
        return category, tags[:5]  # Limit to 5 tags
    
    async def ensure_knowledge_base_exists(self, category: str) -> str:
        """Create knowledge base if it doesn't exist, return its ID."""
        # First check the cache
        if category in self.knowledge_bases:
            return self.knowledge_bases[category]
        
        # Convert category to display name for searching
        kb_name = category.replace('_', ' ').title()
        
        # Check if a knowledge base with this name already exists by refreshing from API
        # This prevents duplicate knowledge bases if the cache was outdated
        try:
            response = self.dify_api.get_knowledge_base_list()
            if response.status_code == 200:
                kb_data = response.json()
                
                # Handle different possible response structures (same logic as initialize)
                kb_list = []
                if isinstance(kb_data, dict):
                    if 'data' in kb_data:
                        kb_list = kb_data['data']
                    elif 'datasets' in kb_data:
                        kb_list = kb_data['datasets']
                elif isinstance(kb_data, list):
                    kb_list = kb_data
                
                # Check if knowledge base with this name already exists
                for kb in kb_list:
                    if isinstance(kb, dict):
                        existing_name = kb.get('name') or kb.get('title') or kb.get('dataset_name')
                        kb_id = kb.get('id') or kb.get('dataset_id') or kb.get('uuid')
                        
                        if existing_name and kb_id:
                            # Check for exact match or category match
                            if existing_name == kb_name or existing_name.lower().replace(' ', '_') == category:
                                self.knowledge_bases[category] = kb_id
                                print(f"✅ Found existing knowledge base: {existing_name} (ID: {kb_id})")
                                return kb_id
        except Exception as e:
            print(f"Warning: Could not refresh knowledge base list: {e}")
        
        # Create new knowledge base if none found
        response = self.dify_api.create_empty_knowledge_base(kb_name)
        
        if response.status_code == 200:
            kb_data = response.json()
            print(f"Debug: Create KB response: {kb_data}")
            
            # Handle different possible response structures for creation
            kb_id = None
            if isinstance(kb_data, dict):
                kb_id = kb_data.get('id') or kb_data.get('dataset_id') or kb_data.get('uuid')
                
                # Some APIs return the created object nested
                if not kb_id and 'data' in kb_data:
                    data = kb_data['data']
                    if isinstance(data, dict):
                        kb_id = data.get('id') or data.get('dataset_id') or data.get('uuid')
            
            if kb_id:
                self.knowledge_bases[category] = kb_id
                print(f"✅ Created new knowledge base: {kb_name} (ID: {kb_id})")
                return kb_id
            else:
                print(f"❌ Failed to extract knowledge base ID from response: {kb_data}")
                return None
        else:
            print(f"❌ Failed to create knowledge base '{kb_name}': {response.status_code} - {response.text}")
            return None
    
    async def ensure_tags_exist(self, tags: List[str]) -> List[str]:
        """Create tags if they don't exist, return list of tag IDs."""
        tag_ids = []
        
        for tag_name in tags:
            if tag_name in self.tags_cache:
                tag_ids.append(self.tags_cache[tag_name])
                continue
            
            # Check if tag exists by refreshing from API (prevents duplicates)
            try:
                response = self.dify_api.get_knowledge_base_type_tags()
                if response.status_code == 200:
                    tags_data = response.json()
                    
                    # Handle different possible response structures
                    tag_list = []
                    if isinstance(tags_data, dict):
                        if 'data' in tags_data:
                            tag_list = tags_data['data']
                        elif 'tags' in tags_data:
                            tag_list = tags_data['tags']
                    elif isinstance(tags_data, list):
                        tag_list = tags_data
                    
                    # Check if tag already exists
                    found_existing = False
                    for tag in tag_list:
                        if isinstance(tag, dict):
                            existing_name = tag.get('name') or tag.get('title')
                            tag_id = tag.get('id') or tag.get('tag_id') or tag.get('uuid')
                            
                            if existing_name == tag_name and tag_id:
                                self.tags_cache[tag_name] = tag_id
                                tag_ids.append(tag_id)
                                print(f"✅ Found existing tag: {tag_name} (ID: {tag_id})")
                                found_existing = True
                                break
                    
                    if found_existing:
                        continue
            except Exception as e:
                print(f"Warning: Could not refresh tags list: {e}")
            
            # Create new tag if not found
            response = self.dify_api.create_knowledge_base_type_tag(tag_name)
            if response.status_code == 200:
                tag_data = response.json()
                print(f"Debug: Create tag response: {tag_data}")
                
                # Handle different possible response structures for creation
                tag_id = None
                if isinstance(tag_data, dict):
                    tag_id = tag_data.get('id') or tag_data.get('tag_id') or tag_data.get('uuid')
                    
                    # Some APIs return the created object nested
                    if not tag_id and 'data' in tag_data:
                        data = tag_data['data']
                        if isinstance(data, dict):
                            tag_id = data.get('id') or data.get('tag_id') or data.get('uuid')
                
                if tag_id:
                    self.tags_cache[tag_name] = tag_id
                    tag_ids.append(tag_id)
                    print(f"✅ Created new tag: {tag_name} (ID: {tag_id})")
                else:
                    print(f"❌ Failed to extract tag ID from response: {tag_data}")
            else:
                print(f"❌ Failed to create tag '{tag_name}': {response.status_code} - {response.text}")
        
        return tag_ids
    
    async def push_to_knowledge_base(self, kb_id: str, content_data: dict, index: int) -> bool:
        """Push content to specific knowledge base."""
        markdown_content = content_data.get('description', '')
        
        response = self.dify_api.create_document_from_text(
            dataset_id=kb_id,
            name=f"{content_data.get('title', 'Document')}_{index}",
            text=markdown_content
        )
        
        if response.status_code == 200:
            print(f"✅ Successfully pushed document to knowledge base")
            return True
        else:
            print(f"❌ Failed to push document: {response.text}")
            return False
    
    async def bind_tags_to_knowledge_base(self, kb_id: str, tag_ids: List[str]):
        """Bind tags to knowledge base."""
        if not tag_ids:
            return
            
        response = self.dify_api.bind_dataset_to_tag(tag_ids, kb_id)
        if response.status_code == 200:
            print(f"✅ Successfully bound {len(tag_ids)} tags to knowledge base")
        else:
            print(f"❌ Failed to bind tags: {response.text}")
    
    async def process_crawled_content(self, content_data: dict, url: str, index: int) -> bool:
        """Process a single crawled content item through the complete workflow."""
        try:
            # Analyze content to determine category and tags
            description = content_data.get('description', '')
            category, suggested_tags = self.categorize_content(description, url)
            
            print(f"  📂 Category: {category}")
            print(f"  🏷️  Suggested tags: {', '.join(suggested_tags)}")
            
            # Ensure knowledge base exists
            kb_id = await self.ensure_knowledge_base_exists(category)
            if not kb_id:
                print(f"❌ Could not create or find knowledge base for category '{category}', trying fallback...")
                # Try to create a generic fallback knowledge base
                fallback_kb_id = await self.ensure_knowledge_base_exists("general")
                if not fallback_kb_id:
                    print(f"❌ Even fallback knowledge base failed, skipping content")
                    return False
                kb_id = fallback_kb_id
                print(f"✅ Using fallback knowledge base: general (ID: {kb_id})")
            
            # Push content to knowledge base
            success = await self.push_to_knowledge_base(kb_id, content_data, index)
            if not success:
                return False
            
            # Create and bind tags
            tag_ids = await self.ensure_tags_exist(suggested_tags)
            if tag_ids:
                await self.bind_tags_to_knowledge_base(kb_id, tag_ids)
            
            return True
            
        except Exception as e:
            print(f"❌ Error processing content: {e}")
            return False
    
    async def crawl_and_process(self, url: str, max_pages: int = 10, max_depth: int = 1):
        """Main workflow: crawl website, filter with LLM, and organize in knowledge bases."""
        
        # Initialize workflow
        if not self._initialized:
            await self.initialize()
        else:
            print("📋 Using cached knowledge bases and tags from previous initialization")
        
        if not self.gemini_api_key:
            print("Warning: No GEMINI_API_KEY provided. Set GEMINI_API_KEY environment variable")
            return
        
        # Configure browser settings (keeping original logic)
        browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )
        
        # Load extraction instruction (keeping original logic)
        try:
            with open("prompts/extraction_prompt_optimized.txt", "r") as f:
                instruction = f.read()
        except FileNotFoundError:
            instruction = """Extract comprehensive content from the webpage.
Create detailed sections separated by \\n\\n covering: comprehensive overview, detailed features, 
implementation guide, technical deep-dive, comparative analysis, real-world applications, 
evolution/roadmap, and resources. Target 1500-3000 words total with rich, self-contained 
sections that can answer queries independently. Output only ONE JSON object."""
        
        # Configure LLM extraction strategy (keeping original logic)
        llm_strategy = LLMExtractionStrategy(
            llm_config=LLMConfig(
                provider="gemini/gemini-2.5-flash-lite", 
                api_token=self.gemini_api_key
            ),
            schema=ResultSchema.model_json_schema(),
            extraction_type="schema",
            instruction=instruction,
            chunk_token_threshold=1000000,
            overlap_rate=0.0,
            apply_chunking=False,
            input_format="markdown",
            extra_args={
                "temperature": 0.0,
                "max_tokens": 8000
            }
        )
        
        # Configure crawler (keeping original logic)
        run_config = CrawlerRunConfig(
            deep_crawl_strategy=BFSDeepCrawlStrategy(
                max_depth=max_depth,
                include_external=False,
                max_pages=max_pages
            ),
            extraction_strategy=llm_strategy,
            cache_mode=CacheMode.BYPASS,
            stream=True
        )
        
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        # Initialize and run crawler (keeping original logic but adding workflow processing)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            print(f"🚀 Starting intelligent crawl workflow from: {url}")
            print("📋 Configuration: Crawl → LLM Filter → Smart Knowledge Base Organization")
            print("-" * 80)
            
            result_stream = await crawler.arun(url=url, config=run_config)
            
            crawled_count = 0
            extracted_files = []
            workflow_results = []
            
            try:
                async for page_result in result_stream:
                    if hasattr(page_result, 'url'):
                        crawled_count += 1
                        print(f"\n[Page {crawled_count}] {page_result.url}")
                        print(f"  Status: {'✓' if page_result.success else '✗'}")
                        
                        if not page_result.success:
                            print(f"  Error: {page_result.error_message}")
                            continue
                        
                        if page_result.extracted_content:
                            try:
                                # Parse extracted data (keeping original logic)
                                if isinstance(page_result.extracted_content, str):
                                    extracted_data = json.loads(page_result.extracted_content)
                                else:
                                    extracted_data = page_result.extracted_content
                                
                                if isinstance(extracted_data, list):
                                    if len(extracted_data) > 1:
                                        print(f"  Warning: Multiple entries found ({len(extracted_data)}), using first one")
                                    extracted_data = extracted_data[0] if extracted_data else {}
                                
                                if not extracted_data or not extracted_data.get('description'):
                                    print("  ⏭️  Skipping - no valid content extracted")
                                    continue
                                
                                # Save JSON (keeping original logic)
                                url_filename = page_result.url.replace("https://", "").replace("http://", "")
                                url_filename = url_filename.replace("/", "_").replace("?", "_").replace(":", "_")
                                if len(url_filename) > 100:
                                    url_filename = url_filename[:100]
                                
                                json_file = Path(output_dir) / f"{url_filename}.json"
                                with open(json_file, "w", encoding="utf-8") as f:
                                    json.dump(extracted_data, f, indent=2, ensure_ascii=False)
                                
                                extracted_files.append(str(json_file))
                                print(f"  💾 Saved: {json_file}")
                                
                                # Display summary (keeping original logic)
                                print(f"  📄 Title: {extracted_data.get('title', 'N/A')}")
                                desc = extracted_data.get('description', '')
                                desc_length = len(desc)
                                chunk_count = desc.count('\n\n') + 1
                                print(f"  📝 Description: {desc_length} characters in {chunk_count} chunks")
                                
                                # NEW: Process through intelligent workflow
                                workflow_success = await self.process_crawled_content(
                                    extracted_data, page_result.url, crawled_count
                                )
                                
                                workflow_results.append({
                                    'url': page_result.url,
                                    'title': extracted_data.get('title', 'Untitled'),
                                    'success': workflow_success,
                                    'category': self.categorize_content(desc, page_result.url)[0]
                                })
                                
                            except Exception as e:
                                print(f"  Error processing content: {e}")
                        else:
                            print("  No content extracted")
                        
            except Exception as e:
                print(f"\nError during crawling: {e}")
            
            # Final summary
            print("\n" + "=" * 80)
            print("🎯 INTELLIGENT CRAWL WORKFLOW SUMMARY")
            print("=" * 80)
            print(f"Total pages crawled: {crawled_count}")
            print(f"Total entries extracted: {len(extracted_files)}")
            
            if workflow_results:
                successful = sum(1 for r in workflow_results if r['success'])
                print(f"Knowledge base operations: {successful}/{len(workflow_results)} successful")
                
                # Show knowledge bases created/used
                print(f"\n📚 Knowledge bases: {len(self.knowledge_bases)}")
                for name, kb_id in self.knowledge_bases.items():
                    print(f"  • {name} (ID: {kb_id})")
                
                # Show tags created/used
                print(f"\n🏷️  Tags: {len(self.tags_cache)}")
                for name in self.tags_cache.keys():
                    print(f"  • {name}")
            
            # Show token usage (keeping original logic)
            if hasattr(llm_strategy, 'show_usage'):
                print("\n🔢 Token Usage:")
                llm_strategy.show_usage()


# Example usage and main function
async def main():
    """Example usage of the CrawlWorkflow."""
    load_dotenv(override=True)
    
    # Initialize workflow
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key="dataset-VoYPMEaQ8L1udk2F6oek99XK",  # Replace with your API key
        gemini_api_key=os.getenv('GEMINI_API_KEY')
    )
    
    # Run the complete workflow
    await workflow.crawl_and_process(
        url="https://eosnetwork.com/",
        max_pages=4,
        max_depth=1
    )

if __name__ == "__main__":
    asyncio.run(main())