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
from difflib import SequenceMatcher
import re

# Import the DifyAPI class
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Test_dify import DifyAPI


class CrawlWorkflow:
    def __init__(self, dify_base_url="http://localhost:8088", dify_api_key=None, gemini_api_key=None, use_parent_child=True, naming_model=None):
        """Initialize the crawl workflow with API configurations.
        
        Args:
            dify_base_url: Base URL for Dify API
            dify_api_key: API key for Dify
            gemini_api_key: API key for Gemini (used for both naming and extraction by default)
            use_parent_child: Enable parent-child chunking for extraction
            naming_model: Custom model for knowledge base naming (e.g., "gemini/gemini-1.5-flash" for fast naming)
                         If None, uses the same model as extraction
        """
        self.dify_api = DifyAPI(base_url=dify_base_url, api_key=dify_api_key)
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        self.naming_model = naming_model or "gemini/gemini-1.5-flash"  # Default to fast model for naming
        self.knowledge_bases = {}  # Cache of existing knowledge bases
        self.tags_cache = {}  # Cache of existing tags
        self.document_cache = {}  # Cache of existing documents by knowledge base {kb_id: {doc_name: doc_id}}
        self._initialized = False  # Track initialization state
        self.use_parent_child = use_parent_child  # Enable parent-child chunking
        
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
        self.document_cache.clear()
        await self.initialize()
    
    def generate_document_name(self, url: str, title: str = None) -> str:
        """Generate a consistent document name from URL only (ignoring title for consistency)."""
        # Normalize URL first
        url = url.rstrip('/')  # Remove trailing slash
        
        # Parse URL to get meaningful parts
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        path = parsed.path.strip('/')
        
        # Create base name from domain and path
        if path:
            # Replace slashes with underscores and clean up
            path_clean = path.replace('/', '_').replace('-', '_')
            base_name = f"{domain}_{path_clean}"
        else:
            base_name = domain
        
        # Add query parameters if present (important for different pages)
        if parsed.query:
            # Take first 20 chars of query to differentiate pages
            query_clean = parsed.query[:20].replace('&', '_').replace('=', '_')
            base_name = f"{base_name}_q_{query_clean}"
        
        # NOTE: We intentionally ignore the title parameter to ensure consistent naming
        # between checking (before we have title) and pushing (after we have title)
        
        # Remove special characters and limit length
        base_name = ''.join(c for c in base_name if c.isalnum() or c in ['_', '-', '.'])
        base_name = base_name[:100]  # Limit to 100 chars
        
        return base_name
    
    def preprocess_category_name(self, category: str) -> str:
        """Standardize category names to prevent duplicates."""
        if not category:
            return "general"
        
        # Convert to lowercase
        category = category.lower().strip()
        
        # Handle common patterns that should be the same
        replacements = {
            'grow a garden': 'growagarden',
            'grow_a_garden': 'growagarden',
            'grow-a-garden': 'growagarden',
            'eos network': 'eos',
            'eos_network': 'eos',
            'eos-network': 'eos',
            'bitcoin btc': 'bitcoin',
            'btc bitcoin': 'bitcoin',
            'ethereum eth': 'ethereum',
            'eth ethereum': 'ethereum',
            'react js': 'react',
            'reactjs': 'react',
            'react.js': 'react',
        }
        
        # Direct replacements
        for old, new in replacements.items():
            if category == old:
                category = new
                break
        
        # Remove common articles and join words
        articles = ['a', 'an', 'the']
        words = re.split(r'[\s_-]+', category)
        words = [w for w in words if w and w not in articles]
        
        # For short phrases, remove spaces/underscores/hyphens
        if len(words) <= 3:
            category = ''.join(words)
        else:
            # For longer phrases, use underscores
            category = '_'.join(words)
        
        return category[:50]  # Limit length
    
    def find_best_matching_kb(self, new_category: str, threshold: float = 0.85) -> str:
        """Find existing KB that matches closely using fuzzy matching."""
        if not self.knowledge_bases:
            return new_category
        
        # Normalize for comparison
        def normalize(text):
            return re.sub(r'[^a-z0-9]', '', text.lower())
        
        new_normalized = normalize(new_category)
        if not new_normalized:
            return new_category
        
        best_match = None
        best_score = 0
        
        for existing_kb in self.knowledge_bases.keys():
            existing_normalized = normalize(existing_kb)
            
            # Check exact match after normalization
            if new_normalized == existing_normalized:
                print(f"  🎯 Exact match: '{new_category}' → '{existing_kb}'")
                return existing_kb
            
            # Check similarity ratio
            similarity = SequenceMatcher(None, new_normalized, existing_normalized).ratio()
            if similarity > best_score:
                best_match = existing_kb
                best_score = similarity
        
        # Use best match if above threshold
        if best_score >= threshold:
            print(f"  🔄 Fuzzy match: '{new_category}' → '{best_match}' (similarity: {best_score:.2%})")
            return best_match
        
        return new_category
    
    def extract_keywords(self, text: str) -> set:
        """Extract main keywords from category name."""
        if not text:
            return set()
        
        # Remove common words
        stopwords = {'a', 'an', 'the', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'with'}
        words = re.split(r'[\s_-]+', text.lower())
        keywords = {w for w in words if w not in stopwords and len(w) > 2}
        return keywords
    
    def find_kb_by_keywords(self, new_category: str, threshold: float = 0.6) -> str:
        """Find KB with matching keywords as backup method."""
        if not self.knowledge_bases:
            return new_category
        
        new_keywords = self.extract_keywords(new_category)
        if not new_keywords:
            return new_category
        
        best_match = None
        best_score = 0
        
        for kb_name in self.knowledge_bases.keys():
            kb_keywords = self.extract_keywords(kb_name)
            if not kb_keywords:
                continue
            
            # Calculate Jaccard similarity (intersection over union)
            intersection = len(new_keywords & kb_keywords)
            union = len(new_keywords | kb_keywords)
            score = intersection / union if union > 0 else 0
            
            if score > best_score:
                best_match = kb_name
                best_score = score
        
        # Use keyword match if above threshold
        if best_score >= threshold:
            print(f"  🔑 Keyword match: '{new_category}' → '{best_match}' (score: {best_score:.2%})")
            return best_match
        
        return new_category
    
    async def categorize_content(self, content: str, url: str) -> Tuple[str, List[str]]:
        """Smart content categorization with duplicate prevention."""
        domain = urlparse(url).netloc.lower()
        
        # Step 1: Try LLM categorization
        category = None
        tags = []
        
        try:
            # Prepare content sample for analysis (first 1000 chars for efficiency)
            content_sample = content[:1000] if len(content) > 1000 else content
            
            # Create prompt for LLM categorization
            categorization_prompt = f"""Analyze this content and provide a GENERAL knowledge base category name and relevant tags.

URL: {url}
Domain: {domain}
Content sample: {content_sample}

Instructions:
1. Create a GENERAL category name that groups ALL related content together
2. Use ONLY the main technology/platform name, nothing else
3. Keep it as SHORT as possible (1-2 words max)
4. Use snake_case only if necessary (prefer single word)
5. DO NOT add descriptors like "_documentation", "_tutorial", "_development"
6. Generate 3-5 relevant tags that describe the content

Output format (JSON):
{{
  "category": "general_category_name",
  "tags": ["tag1", "tag2", "tag3"]
}}

Examples:
- For ANY EOS-related content: {{"category": "eos", "tags": ["eos", "blockchain", "web3"]}}
- For ANY Bitcoin content: {{"category": "bitcoin", "tags": ["bitcoin", "cryptocurrency", "btc"]}}
- For ANY Ethereum content: {{"category": "ethereum", "tags": ["ethereum", "blockchain", "eth"]}}
- For ANY React content: {{"category": "react", "tags": ["react", "javascript", "frontend"]}}
"""
            
            # Use the configured naming model for categorization
            # For now, we'll use a simple API call approach
            # TODO: Implement proper model switching when crawl4ai supports it
            
            print(f"  🤖 Using naming model: {self.naming_model}")
            
            # Use direct Gemini API call (will be replaced with proper model switching later)
            import requests
            
            # Extract model type and determine API endpoint
            if "gemini" in self.naming_model.lower():
                model_name = self.naming_model.split("/")[-1] if "/" in self.naming_model else "gemini-1.5-flash"
                
                headers = {
                    'Content-Type': 'application/json',
                }
                
                data = {
                    "contents": [{
                        "parts": [{
                            "text": categorization_prompt
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.2,  # Lower temperature for consistent naming
                        "maxOutputTokens": 256,
                        "topK": 40,
                        "topP": 0.95
                    }
                }
                
                response = requests.post(
                    f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_api_key}',
                    headers=headers,
                    json=data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text_response = result['candidates'][0]['content']['parts'][0]['text']
                    print(f"  🤖 Naming model response: {text_response[:100]}...")
                
                # Parse JSON response
                json_match = re.search(r'\{[^}]+\}', text_response)
                if json_match:
                    categorization_data = json.loads(json_match.group())
                    category = categorization_data.get('category', 'general')
                    tags = categorization_data.get('tags', [])
                    
                    if category and isinstance(tags, list):
                        print(f"  🤖 Raw naming result: {category}")
                        
                        # Step 2: Preprocess/normalize the category name
                        category = self.preprocess_category_name(category)
                        print(f"  📝 Normalized: {category}")
                        
                        # Step 3: Check for fuzzy matches with existing KBs (saves tokens!)
                        matched_category = self.find_best_matching_kb(category, threshold=0.85)
                        if matched_category != category:
                            category = matched_category
                        else:
                            # Step 4: Try keyword matching as backup
                            keyword_matched = self.find_kb_by_keywords(category, threshold=0.6)
                            if keyword_matched != category:
                                category = keyword_matched
                        
                        # Add domain tag
                        domain_tag = domain.replace('.', '_')
                        if domain_tag not in tags:
                            tags.append(domain_tag)
                        
                        return category, tags[:5]
            
        except Exception as e:
            print(f"  ⚠️  LLM categorization failed: {e}, using fallback")
        
        # Step 5: Fallback to enhanced rule-based categorization
        print(f"  🔧 Using enhanced rule-based fallback")
        category = "general"
        tags = []
        
        # Prepare content sample for analysis
        content_lower = content[:500].lower() if len(content) > 500 else content.lower()
        
        # Domain-based categorization with general names
        if 'eos' in domain or 'eos' in content_lower:
            category = "eos"
            tags.extend(["eos", "blockchain"])
        elif 'bitcoin' in domain or any(term in content_lower for term in ['bitcoin', 'btc']):
            category = "bitcoin"
            tags.extend(["bitcoin", "cryptocurrency"])
        elif 'ethereum' in domain or any(term in content_lower for term in ['ethereum', 'eth']):
            category = "ethereum"
            tags.extend(["ethereum", "blockchain"])
        elif 'solana' in domain or 'solana' in content_lower:
            category = "solana"
            tags.extend(["solana", "blockchain"])
        elif 'cardano' in domain or any(term in content_lower for term in ['cardano', 'ada']):
            category = "cardano"
            tags.extend(["cardano", "blockchain"])
        elif 'polkadot' in domain or any(term in content_lower for term in ['polkadot', 'dot']):
            category = "polkadot"
            tags.extend(["polkadot", "blockchain"])
        elif any(term in domain for term in ['news', 'blog']):
            category = "news_blogs"
            tags.append("news")
        elif any(term in domain for term in ['github', 'gitlab']):
            category = "code_repos"
            tags.append("code")
        else:
            # Content-based categorization
            if 'react' in content_lower:
                category = "react"
                tags.extend(["react", "javascript"])
            elif 'vue' in content_lower:
                category = "vue"
                tags.extend(["vue", "javascript"])
            elif 'angular' in content_lower:
                category = "angular"
                tags.extend(["angular", "javascript"])
            elif 'python' in content_lower:
                category = "python"
                tags.extend(["python", "programming"])
            elif any(term in content_lower for term in ['javascript', 'js']):
                category = "javascript"
                tags.extend(["javascript", "programming"])
            elif 'java' in content_lower and 'javascript' not in content_lower:
                category = "java"
                tags.extend(["java", "programming"])
            elif any(tech in content_lower for tech in ['blockchain', 'crypto', 'defi', 'web3']):
                category = "blockchain"
                tags.append("blockchain")
            elif any(tech in content_lower for tech in ['ai', 'machine learning', 'artificial intelligence', 'ml']):
                category = "ai_ml"
                tags.extend(["ai", "machine_learning"])
            elif 'api' in content_lower:
                category = "api_docs"
                tags.append("api")
        
        # Step 6: Apply smart matching to fallback result too
        print(f"  🔧 Fallback result: {category}")
        
        # Normalize the fallback category
        category = self.preprocess_category_name(category)
        print(f"  📝 Normalized fallback: {category}")
        
        # Check for matches with existing KBs
        matched_category = self.find_best_matching_kb(category, threshold=0.85)
        if matched_category != category:
            category = matched_category
        else:
            # Try keyword matching
            keyword_matched = self.find_kb_by_keywords(category, threshold=0.6)
            if keyword_matched != category:
                category = keyword_matched
        
        # Add domain tag
        domain_tag = domain.replace('.', '_')
        if domain_tag not in tags:
            tags.append(domain_tag)
        
        return category, list(set(tags))[:5]
    
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
    
    async def load_documents_for_knowledge_base(self, kb_id: str) -> dict:
        """Load all documents for a specific knowledge base into cache."""
        if kb_id in self.document_cache:
            return self.document_cache[kb_id]
        
        documents = {}
        page = 1
        
        try:
            while True:
                response = self.dify_api.get_document_list(kb_id, page=page, limit=100)
                if response.status_code != 200:
                    print(f"❌ Failed to get documents for KB {kb_id}: {response.status_code}")
                    break
                
                data = response.json()
                doc_list = data.get('data', [])
                
                if not doc_list:
                    break
                
                for doc in doc_list:
                    doc_name = doc.get('name', '')
                    doc_id = doc.get('id', '')
                    if doc_name and doc_id:
                        documents[doc_name] = doc_id
                
                # Check if there are more pages
                if not data.get('has_more', False):
                    break
                    
                page += 1
            
            self.document_cache[kb_id] = documents
            print(f"📚 Loaded {len(documents)} existing documents for knowledge base {kb_id}")
            
        except Exception as e:
            print(f"❌ Error loading documents for KB {kb_id}: {e}")
            self.document_cache[kb_id] = {}
        
        return documents
    
    async def check_url_exists(self, url: str) -> Tuple[bool, str, str]:
        """Check if a URL already exists in any knowledge base.
        Returns: (exists, kb_id, doc_name)
        """
        # Normalize URL before checking
        url = url.rstrip('/')
        
        # Generate the document name that would be used for this URL
        doc_name = self.generate_document_name(url)
        
        # Check each knowledge base for this document
        for kb_name, kb_id in self.knowledge_bases.items():
            # Load documents for this KB if not already cached
            if kb_id not in self.document_cache:
                await self.load_documents_for_knowledge_base(kb_id)
            
            # Check if document exists in this KB
            if doc_name in self.document_cache.get(kb_id, {}):
                return True, kb_id, doc_name
        
        return False, None, doc_name
    
    async def preload_all_documents(self):
        """Preload all documents from all knowledge bases for efficient checking."""
        print("📚 Preloading all documents from knowledge bases...")
        total_docs = 0
        
        for kb_name, kb_id in self.knowledge_bases.items():
            docs = await self.load_documents_for_knowledge_base(kb_id)
            total_docs += len(docs)
        
        print(f"✅ Preloaded {total_docs} documents from {len(self.knowledge_bases)} knowledge bases")
    
    async def push_to_knowledge_base(self, kb_id: str, content_data: dict, url: str) -> Tuple[bool, str]:
        """Push content to specific knowledge base with duplicate detection.
        Returns: (success, status_message)
        """
        # Normalize URL
        url = url.rstrip('/')
        
        markdown_content = content_data.get('description', '')
        title = content_data.get('title', 'Document')
        
        # Generate consistent document name based on URL (title is ignored)
        doc_name = self.generate_document_name(url, title)
        print(f"  🔍 Document name for push: {doc_name}")
        
        # Load existing documents for this knowledge base
        existing_docs = await self.load_documents_for_knowledge_base(kb_id)
        
        # Check if document already exists
        if doc_name in existing_docs:
            print(f"⏭️  Document already exists: {doc_name} (ID: {existing_docs[doc_name]})")
            return True, "skipped_existing"
        
        # Create new document with parent-child support
        response = self.dify_api.create_document_from_text(
            dataset_id=kb_id,
            name=doc_name,
            text=markdown_content,
            use_parent_child=self.use_parent_child
        )
        
        if response.status_code == 200:
            # Update cache with new document
            doc_data = response.json()
            print(f"  📄 Document creation response: {json.dumps(doc_data, indent=2)}")
            
            doc_id = doc_data.get('id') or doc_data.get('document', {}).get('id')
            if doc_id:
                existing_docs[doc_name] = doc_id
                print(f"✅ Successfully pushed new document: {doc_name} (ID: {doc_id})")
            else:
                print(f"⚠️  Document created but no ID returned: {doc_name}")
                print(f"  Response structure: {list(doc_data.keys())}")
            
            # Check indexing status if available
            indexing_status = doc_data.get('indexing_status') or doc_data.get('document', {}).get('indexing_status')
            if indexing_status:
                print(f"  📊 Indexing status: {indexing_status}")
                
            return True, "created_new"
        else:
            print(f"❌ Failed to push document: {response.status_code}")
            print(f"  Error response: {response.text}")
            return False, "failed"
    
    async def bind_tags_to_knowledge_base(self, kb_id: str, tag_ids: List[str]):
        """Bind tags to knowledge base."""
        if not tag_ids:
            return
            
        response = self.dify_api.bind_dataset_to_tag(tag_ids, kb_id)
        if response.status_code == 200:
            print(f"✅ Successfully bound {len(tag_ids)} tags to knowledge base")
        else:
            print(f"❌ Failed to bind tags: {response.text}")
    
    async def process_crawled_content(self, content_data: dict, url: str) -> Tuple[bool, str]:
        """Process a single crawled content item through the complete workflow.
        Returns: (success, status)
        """
        try:
            # Analyze content to determine category and tags
            description = content_data.get('description', '')
            category, suggested_tags = await self.categorize_content(description, url)
            
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
                    return False, "failed_kb_creation"
                kb_id = fallback_kb_id
                print(f"✅ Using fallback knowledge base: general (ID: {kb_id})")
            
            # Push content to knowledge base with duplicate detection
            success, status = await self.push_to_knowledge_base(kb_id, content_data, url)
            
            # Only bind tags if document was newly created
            if success and status == "created_new":
                # Create and bind tags
                tag_ids = await self.ensure_tags_exist(suggested_tags)
                if tag_ids:
                    await self.bind_tags_to_knowledge_base(kb_id, tag_ids)
            
            return success, status
            
        except Exception as e:
            print(f"❌ Error processing content: {e}")
            return False, "error"
    
    async def crawl_and_process(self, url: str, max_pages: int = 10, max_depth: int = 1, extraction_model: str = "gemini/gemini-2.0-flash-exp"):
        """Main workflow: crawl website, check duplicates BEFORE extraction, and organize in knowledge bases.
        
        Args:
            url: The starting URL to crawl
            max_pages: Maximum number of pages to crawl
            max_depth: Maximum depth for deep crawling
            extraction_model: The LLM model to use for content extraction
        
        Note: 
            - Uses self.naming_model for knowledge base categorization (fast model)
            - Uses extraction_model for content extraction (smart model)
        """
        
        # Initialize workflow
        if not self._initialized:
            await self.initialize()
        else:
            print("📋 Using cached knowledge bases and tags from previous initialization")
        
        # Preload all documents for efficient duplicate checking
        await self.preload_all_documents()
        
        if not self.gemini_api_key:
            print("Warning: No GEMINI_API_KEY provided. Set GEMINI_API_KEY environment variable")
            return
        
        # Configure browser settings (keeping original logic)
        browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )
        
        # Load extraction instruction based on chunking mode
        if self.use_parent_child:
            prompt_file = "prompts/extraction_prompt_parent_child.txt"
            fallback_prompt = """You are a RAG Professor creating parent-child hierarchical chunks. Extract content with PARENT sections (###PARENT_SECTION###) providing overview and CHILD sections (###CHILD_SECTION###) containing details. Each parent should have 2-5 children. Parents: 500-1500 words, Children: 200-800 words. Output ONE JSON with title, name, and description fields."""
        else:
            prompt_file = "prompts/extraction_prompt_flexible.txt"
            fallback_prompt = """You are a RAG content extractor optimizing for systems that return ~10 chunks. Extract comprehensive content where EACH SECTION is a COMPLETE, standalone resource.

Create 4-8 logical sections with descriptive titles in brackets. Each section MUST contain ALL information needed to fully answer queries about its topic.

CRITICAL RULES:
1. Each section should be 300-1500 words and 100% self-contained
2. NEVER split sequential steps across sections - if you see "Step 1, Step 2, Step 3", keep ALL steps together
3. For processes (account creation, wallet setup, installations), include EVERYTHING in ONE section:
   - ALL prerequisites
   - ALL options/choices
   - ALL steps from start to finish
   - ALL troubleshooting
   - ALL next steps
4. Include deliberate redundancy - repeat full information wherever relevant

Target 3000-6000 words total with sections separated by ###SECTION_BREAK###. Output only ONE JSON object with title, name, and description fields."""
            
        try:
            with open(prompt_file, "r") as f:
                instruction = f.read()
                print(f"✅ Loaded extraction prompt successfully ({len(instruction)} characters)")
                print(f"📝 Using {'parent-child' if self.use_parent_child else 'flat'} chunking mode")
                # Debug: Show first 200 chars to verify correct prompt
                print(f"📝 Prompt preview: {instruction[:200]}...")
        except FileNotFoundError:
            print(f"⚠️ {prompt_file} not found, using fallback")
            # Fallback to flexible approach if file not found
            instruction = fallback_prompt
        
        # Configure LLM extraction strategy with extraction model (smart model)
        print(f"🧠 Using models:")
        print(f"  📝 Naming: {self.naming_model} (fast)")
        print(f"  🔍 Extraction: {extraction_model} (smart)")
        
        llm_strategy = LLMExtractionStrategy(
            llm_config=LLMConfig(
                provider=extraction_model,  # Use the extraction model parameter
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
                "max_tokens": 32000  # Increased to support comprehensive chunks
            }
        )
        
        # First, collect URLs without extraction to check for duplicates
        print("\n🔍 Phase 1: Collecting URLs and checking for duplicates...")
        
        # Configure URL collection (no extraction)
        url_collection_config = CrawlerRunConfig(
            deep_crawl_strategy=BFSDeepCrawlStrategy(
                max_depth=max_depth,
                include_external=False,
                max_pages=max_pages
            ),
            extraction_strategy=None,  # No extraction in first pass
            cache_mode=CacheMode.BYPASS,
            stream=True
        )
        
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        # Phase 1: Collect URLs and check for duplicates
        urls_to_process = []
        duplicate_urls = []
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            print(f"🚀 Starting intelligent crawl workflow from: {url}")
            print("📋 Configuration: Check Duplicates → Extract New → Organize in Knowledge Base")
            print("-" * 80)
            
            # First pass: collect URLs
            result_stream = await crawler.arun(url=url, config=url_collection_config)
            
            crawled_count = 0
            
            try:
                async for page_result in result_stream:
                    if hasattr(page_result, 'url'):
                        crawled_count += 1
                        
                        if crawled_count > max_pages:
                            break
                        
                        if page_result.success:
                            # Check if URL already exists in any knowledge base
                            exists, kb_id, doc_name = await self.check_url_exists(page_result.url)
                            
                            if exists:
                                duplicate_urls.append(page_result.url)
                                print(f"⏭️  [Page {crawled_count}] {page_result.url}")
                                print(f"    Already exists as: '{doc_name}' in KB: {kb_id}")
                            else:
                                urls_to_process.append(page_result.url)
                                print(f"✅ [Page {crawled_count}] {page_result.url}")
                                print(f"    Will be saved as: '{doc_name}' - New URL to process")
                        
                        
            except Exception as e:
                print(f"\nError during URL collection: {e}")
            
            # Phase 1 Summary
            print(f"\n📄 Phase 1 Complete:")
            print(f"  Total URLs found: {crawled_count}")
            print(f"  Duplicate URLs skipped: {len(duplicate_urls)}")
            print(f"  New URLs to process: {len(urls_to_process)}")
            
            if not urls_to_process:
                print("\n✅ All URLs already exist in knowledge base. No new content to extract!")
                return
            
            # Phase 2: Extract content only for new URLs
            print(f"\n🔍 Phase 2: Extracting content for {len(urls_to_process)} new URLs...")
            print("-" * 80)
            
            extracted_files = []
            workflow_results = []
            extraction_failures = 0
            
            # Configure extraction for individual URLs
            extraction_config = CrawlerRunConfig(
                extraction_strategy=llm_strategy,
                cache_mode=CacheMode.BYPASS
            )
            
            # Process each new URL
            for idx, process_url in enumerate(urls_to_process, 1):
                print(f"\n[{idx}/{len(urls_to_process)}] Processing: {process_url}")
                
                retry_count = 0
                max_retries = 2
                extraction_successful = False
                
                while retry_count <= max_retries and not extraction_successful:
                    try:
                        if retry_count > 0:
                            print(f"  🔄 Retry attempt {retry_count}/{max_retries}...")
                            await asyncio.sleep(2)  # Brief delay before retry
                        
                        result = await crawler.arun(url=process_url, config=extraction_config)
                        
                        if result.success and result.extracted_content:
                            # Parse extracted data
                            if isinstance(result.extracted_content, str):
                                extracted_data = json.loads(result.extracted_content)
                            else:
                                extracted_data = result.extracted_content
                            
                            if isinstance(extracted_data, list):
                                extracted_data = extracted_data[0] if extracted_data else {}
                            
                            if extracted_data and extracted_data.get('description'):
                                # Save JSON
                                url_filename = process_url.replace("https://", "").replace("http://", "")
                                url_filename = url_filename.replace("/", "_").replace("?", "_").replace(":", "_")
                                if len(url_filename) > 100:
                                    url_filename = url_filename[:100]
                                
                                json_file = Path(output_dir) / f"{url_filename}.json"
                                with open(json_file, "w", encoding="utf-8") as f:
                                    json.dump(extracted_data, f, indent=2, ensure_ascii=False)
                                
                                extracted_files.append(str(json_file))
                                print(f"  💾 Saved: {json_file}")
                                
                                # Display summary
                                print(f"  📄 Title: {extracted_data.get('title', 'N/A')}")
                                desc = extracted_data.get('description', '')
                                desc_length = len(desc)
                                if self.use_parent_child:
                                    parent_count = desc.count('###PARENT_SECTION###') + 1
                                    child_count = desc.count('###CHILD_SECTION###')
                                    print(f"  📝 Description: {desc_length} characters in {parent_count} parent chunks with {child_count} child chunks")
                                else:
                                    chunk_count = desc.count('###SECTION_BREAK###') + 1
                                    print(f"  📝 Description: {desc_length} characters in {chunk_count} chunks")
                                
                                # Process through workflow
                                workflow_success, status = await self.process_crawled_content(
                                    extracted_data, process_url
                                )
                                
                                workflow_results.append({
                                    'url': process_url,
                                    'title': extracted_data.get('title', 'Untitled'),
                                    'success': workflow_success,
                                    'status': status,
                                    'category': (await self.categorize_content(desc, process_url))[0]
                                })
                                
                                extraction_successful = True
                            else:
                                print(f"  ⚠️  No valid content extracted")
                                if retry_count < max_retries:
                                    retry_count += 1
                                else:
                                    extraction_failures += 1
                                    break
                        else:
                            print(f"  ⚠️  Extraction failed: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
                            if retry_count < max_retries:
                                retry_count += 1
                            else:
                                extraction_failures += 1
                                break
                                
                    except Exception as e:
                        print(f"  ❌ Error: {e}")
                        if retry_count < max_retries:
                            retry_count += 1
                        else:
                            extraction_failures += 1
                            break
            
            # Final summary
            print("\n" + "=" * 80)
            print("🎯 INTELLIGENT CRAWL WORKFLOW SUMMARY")
            print("=" * 80)
            print(f"Total URLs discovered: {crawled_count}")
            print(f"Duplicate URLs skipped (saved tokens): {len(duplicate_urls)}")
            print(f"New URLs processed: {len(urls_to_process)}")
            print(f"Extraction failures: {extraction_failures}")
            print(f"Total documents saved: {len(extracted_files)}")
            
            if workflow_results:
                successful = sum(1 for r in workflow_results if r['success'])
                created_new = sum(1 for r in workflow_results if r.get('status') == 'created_new')
                skipped_existing = sum(1 for r in workflow_results if r.get('status') == 'skipped_existing')
                failed = sum(1 for r in workflow_results if not r['success'])
                
                print(f"Knowledge base operations: {successful}/{len(workflow_results)} successful")
                print(f"  ✅ New documents created: {created_new}")
                print(f"  ⏭️  Existing documents skipped: {skipped_existing}")
                print(f"  ❌ Failed operations: {failed}")
                
                # Show knowledge bases created/used
                print(f"\n📚 Knowledge bases: {len(self.knowledge_bases)}")
                for name, kb_id in self.knowledge_bases.items():
                    print(f"  • {name} (ID: {kb_id})")
                
                # Show tags created/used
                print(f"\n🏷️  Tags: {len(self.tags_cache)}")
                for name in self.tags_cache.keys():
                    print(f"  • {name}")
                
                # Show documents cached
                total_docs_cached = sum(len(docs) for docs in self.document_cache.values())
                print(f"\n📄 Total documents tracked: {total_docs_cached}")
            
            # Show token usage (keeping original logic)
            if hasattr(llm_strategy, 'show_usage'):
                print("\n🔢 Token Usage:")
                llm_strategy.show_usage()


# Example usage and main function
async def main():
    """Example usage of the CrawlWorkflow with dual-model setup."""
    load_dotenv(override=True)
    
    # Initialize workflow with dual-model configuration
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key="dataset-VoYPMEaQ8L1udk2F6oek99XK",  # Replace with your API key
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        use_parent_child=True,  # Enable parent-child hierarchical chunking
        naming_model="gemini/gemini-1.5-flash"  # Fast model for naming (cheap & fast)
    )
    
    # Run the complete workflow with dual-model setup
    await workflow.crawl_and_process(
        url="https://docs.eosnetwork.com/",
        max_pages=20,
        max_depth=0,
        extraction_model="gemini/gemini-2.0-flash-exp"  # Smart model for extraction (powerful)
    )

if __name__ == "__main__":
    asyncio.run(main())