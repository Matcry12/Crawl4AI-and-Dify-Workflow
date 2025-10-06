import asyncio
import json
import os
import logging
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse
from datetime import datetime

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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from api.dify_api_resilient import ResilientDifyAPI
from core.content_processor import ContentProcessor, ProcessingMode
from core.resilience_utils import CrawlCheckpoint, FailureQueue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class CrawlWorkflow:
    def __init__(self, dify_base_url="http://localhost:8088", dify_api_key=None, gemini_api_key=None, use_parent_child=True, naming_model=None, knowledge_base_mode='automatic', selected_knowledge_base=None, enable_dual_mode=True, word_threshold=4000, token_threshold=8000, use_word_threshold=True, use_intelligent_mode=False, intelligent_analysis_model="gemini/gemini-1.5-flash", manual_mode=None, custom_llm_base_url=None, custom_llm_api_key=None, enable_resilience=True, checkpoint_file="crawl_checkpoint.json"):
        """Initialize the crawl workflow with API configurations.

        Args:
            dify_base_url: Base URL for Dify API
            dify_api_key: API key for Dify
            gemini_api_key: API key for Gemini (used for both naming and extraction by default)
            use_parent_child: Enable parent-child chunking for extraction (deprecated when dual mode is enabled)
            naming_model: Custom model for knowledge base naming (e.g., "gemini/gemini-1.5-flash" for fast naming)
                         If None, uses the same model as extraction
            knowledge_base_mode: 'automatic' or 'manual' - how to select knowledge base
            selected_knowledge_base: ID of the manually selected knowledge base (when mode is 'manual')
            enable_dual_mode: Enable automatic selection between paragraph and full doc modes
            word_threshold: Word count threshold for mode selection (default 4000)
            token_threshold: Token count threshold for mode selection (default 8000)
            use_word_threshold: If True, use word count; if False, use token count
            use_intelligent_mode: If True, use LLM to analyze content structure and value
            intelligent_analysis_model: Model to use for intelligent content analysis
            enable_resilience: Enable retry logic and circuit breakers (default True)
            checkpoint_file: Path to checkpoint file for crash recovery
        """
        # Use resilient Dify API with retry and circuit breaker
        self.dify_api = ResilientDifyAPI(
            base_url=dify_base_url,
            api_key=dify_api_key,
            enable_retry=enable_resilience,
            enable_circuit_breaker=enable_resilience
        )
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        self.naming_model = naming_model or "gemini/gemini-1.5-flash"  # Default to fast model for naming
        self.knowledge_bases = {}  # Cache of existing knowledge bases
        self.document_cache = {}  # Cache of existing documents by knowledge base {kb_id: {doc_name: doc_id}}
        self.metadata_cache = {}  # Cache of metadata fields by knowledge base {kb_id: {name: {id, type}}}
        self._initialized = False  # Track initialization state
        self.use_parent_child = use_parent_child  # Enable parent-child chunking (deprecated with dual mode)
        self.knowledge_base_mode = knowledge_base_mode  # 'automatic' or 'manual'
        self.selected_knowledge_base = selected_knowledge_base  # ID for manual mode
        self.enable_dual_mode = enable_dual_mode  # Enable automatic mode selection
        self.use_intelligent_mode = use_intelligent_mode  # Enable intelligent content analysis
        self.manual_mode = manual_mode  # Manual selection: 'full_doc' or 'paragraph'
        self.custom_llm_base_url = custom_llm_base_url  # Custom LLM endpoint
        self.custom_llm_api_key = custom_llm_api_key  # Custom LLM API key

        # Initialize resilience features
        self.checkpoint = CrawlCheckpoint(checkpoint_file)
        self.failure_queue = FailureQueue("failure_queue.json")
        self.enable_resilience = enable_resilience
        logger.info(f"🛡️  Resilience features {'enabled' if enable_resilience else 'disabled'}")
        
        # Initialize content processor for dual-mode handling
        self.content_processor = ContentProcessor(
            word_threshold=word_threshold,
            token_threshold=token_threshold,
            use_word_threshold=use_word_threshold,
            use_intelligent_mode=use_intelligent_mode,
            llm_api_key=gemini_api_key if use_intelligent_mode else None,
            analysis_model=intelligent_analysis_model,
            custom_llm_base_url=custom_llm_base_url if use_intelligent_mode else None,
            custom_llm_api_key=custom_llm_api_key if use_intelligent_mode else None
        )
        
    async def initialize(self):
        """Initialize workflow by fetching existing knowledge bases."""
        try:
            # Get existing knowledge bases
            response = self.dify_api.get_knowledge_base_list()
            if response.status_code == 200:
                kb_data = response.json()
                logger.debug(f"Knowledge bases response: {kb_data}")

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
                                logger.info(f"  ✅ Found existing knowledge base: {kb_name} (ID: {kb_id})")
                            else:
                                logger.warning(f"  ⚠️  Skipping knowledge base with incomplete data: {kb}")
                    except Exception as kb_error:
                        logger.warning(f"  ⚠️  Error processing knowledge base entry: {kb_error}")
                        continue
            else:
                logger.error(f"Failed to get knowledge bases: {response.status_code} - {response.text}")
            
                        
        except Exception as e:
            logger.warning(f"Could not initialize existing data: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._initialized = True
            logger.info(f"📊 Initialization complete: {len(self.knowledge_bases)} knowledge bases cached")
    
    async def refresh_cache(self):
        """Force refresh of knowledge bases cache from API."""
        logger.info("🔄 Refreshing cache from API...")
        self.knowledge_bases.clear()
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
                logger.info(f"  🎯 Exact match: '{new_category}' → '{existing_kb}'")
                return existing_kb

            # Check similarity ratio
            similarity = SequenceMatcher(None, new_normalized, existing_normalized).ratio()
            if similarity > best_score:
                best_match = existing_kb
                best_score = similarity

        # Use best match if above threshold
        if best_score >= threshold:
            logger.info(f"  🔄 Fuzzy match: '{new_category}' → '{best_match}' (similarity: {best_score:.2%})")
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
            logger.info(f"  🔑 Keyword match: '{new_category}' → '{best_match}' (score: {best_score:.2%})")
            return best_match
        
        return new_category
    
    async def categorize_content(self, content: str, url: str) -> str:
        """Smart content categorization with duplicate prevention."""
        domain = urlparse(url).netloc.lower()
        
        # Step 1: Try LLM categorization
        category = None
        
        try:
            # Prepare content sample for analysis (first 1000 chars for efficiency)
            content_sample = content[:1000] if len(content) > 1000 else content
            
            # Create prompt for LLM categorization
            categorization_prompt = f"""Analyze this content and provide a GENERAL knowledge base category name.

URL: {url}
Domain: {domain}
Content sample: {content_sample}

Instructions:
1. Create a GENERAL category name that groups ALL related content together
2. Use ONLY the main technology/platform name, nothing else
3. Keep it as SHORT as possible (1-2 words max)
4. Use snake_case only if necessary (prefer single word)
5. DO NOT add descriptors like "_documentation", "_tutorial", "_development"

Output format (JSON):
{{
  "category": "general_category_name"
}}

Examples:
- For ANY EOS-related content: {{"category": "eos"}}
- For ANY Bitcoin content: {{"category": "bitcoin"}}
- For ANY Ethereum content: {{"category": "ethereum"}}
- For ANY React content: {{"category": "react"}}
"""
            
            # Use the configured naming model for categorization
            # For now, we'll use a simple API call approach
            # TODO: Implement proper model switching when crawl4ai supports it

            logger.info(f"  🤖 Using naming model: {self.naming_model}")

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
                    logger.info(f"  🤖 Naming model response: {text_response[:100]}...")

                # Parse JSON response
                json_match = re.search(r'\{[^}]+\}', text_response)
                if json_match:
                    categorization_data = json.loads(json_match.group())
                    category = categorization_data.get('category', 'general')

                    if category:
                        logger.info(f"  🤖 Raw naming result: {category}")

                        # Step 2: Preprocess/normalize the category name
                        category = self.preprocess_category_name(category)
                        logger.info(f"  📝 Normalized: {category}")
                        
                        # Step 3: Check for fuzzy matches with existing KBs (saves tokens!)
                        matched_category = self.find_best_matching_kb(category, threshold=0.85)
                        if matched_category != category:
                            category = matched_category
                        else:
                            # Step 4: Try keyword matching as backup
                            keyword_matched = self.find_kb_by_keywords(category, threshold=0.6)
                            if keyword_matched != category:
                                category = keyword_matched
                        
                        
                        return category
            
        except Exception as e:
            logger.warning(f"  ⚠️  LLM categorization failed: {e}, using fallback")

        # Step 5: Fallback to enhanced rule-based categorization
        logger.info(f"  🔧 Using enhanced rule-based fallback")
        category = "general"
        
        # Prepare content sample for analysis
        content_lower = content[:500].lower() if len(content) > 500 else content.lower()
        
        # Domain-based categorization with general names
        if 'eos' in domain or 'eos' in content_lower:
            category = "eos"
        elif 'bitcoin' in domain or any(term in content_lower for term in ['bitcoin', 'btc']):
            category = "bitcoin"
        elif 'ethereum' in domain or any(term in content_lower for term in ['ethereum', 'eth']):
            category = "ethereum"
        elif 'solana' in domain or 'solana' in content_lower:
            category = "solana"
        elif 'cardano' in domain or any(term in content_lower for term in ['cardano', 'ada']):
            category = "cardano"
        elif 'polkadot' in domain or any(term in content_lower for term in ['polkadot', 'dot']):
            category = "polkadot"
        elif any(term in domain for term in ['news', 'blog']):
            category = "news_blogs"
        elif any(term in domain for term in ['github', 'gitlab']):
            category = "code_repos"
        else:
            # Content-based categorization
            if 'react' in content_lower:
                category = "react"
            elif 'vue' in content_lower:
                category = "vue"
            elif 'angular' in content_lower:
                category = "angular"
            elif 'python' in content_lower:
                category = "python"
            elif any(term in content_lower for term in ['javascript', 'js']):
                category = "javascript"
            elif 'java' in content_lower and 'javascript' not in content_lower:
                category = "java"
            elif any(tech in content_lower for tech in ['blockchain', 'crypto', 'defi', 'web3']):
                category = "blockchain"
            elif any(tech in content_lower for tech in ['ai', 'machine learning', 'artificial intelligence', 'ml']):
                category = "ai_ml"
            elif 'api' in content_lower:
                category = "api_docs"
        
        # Step 6: Apply smart matching to fallback result too
        logger.info(f"  🔧 Fallback result: {category}")

        # Normalize the fallback category
        category = self.preprocess_category_name(category)
        logger.info(f"  📝 Normalized fallback: {category}")
        
        # Check for matches with existing KBs
        matched_category = self.find_best_matching_kb(category, threshold=0.85)
        if matched_category != category:
            category = matched_category
        else:
            # Try keyword matching
            keyword_matched = self.find_kb_by_keywords(category, threshold=0.6)
            if keyword_matched != category:
                category = keyword_matched
        
        return category
    
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
                                logger.info(f"✅ Found existing knowledge base: {existing_name} (ID: {kb_id})")
                                return kb_id
        except Exception as e:
            logger.warning(f"Could not refresh knowledge base list: {e}")
        
        # Create new knowledge base if none found
        response = self.dify_api.create_empty_knowledge_base(kb_name)
        
        if response.status_code == 200:
            kb_data = response.json()
            logger.debug(f"Create KB response: {kb_data}")

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
                logger.info(f"✅ Created new knowledge base: {kb_name} (ID: {kb_id})")
                return kb_id
            else:
                logger.error(f"❌ Failed to extract knowledge base ID from response: {kb_data}")
                return None
        else:
            logger.error(f"❌ Failed to create knowledge base '{kb_name}': {response.status_code} - {response.text}")
            return None
    
    
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
                    logger.error(f"❌ Failed to get documents for KB {kb_id}: {response.status_code}")
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
            logger.info(f"📚 Loaded {len(documents)} existing documents for knowledge base {kb_id}")

        except Exception as e:
            logger.error(f"❌ Error loading documents for KB {kb_id}: {e}")
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
        logger.info("📚 Preloading all documents from knowledge bases...")
        total_docs = 0

        for kb_name, kb_id in self.knowledge_bases.items():
            docs = await self.load_documents_for_knowledge_base(kb_id)
            total_docs += len(docs)

        logger.info(f"✅ Preloaded {total_docs} documents from {len(self.knowledge_bases)} knowledge bases")

    async def ensure_metadata_fields(self, kb_id: str) -> dict:
        """Ensure standard metadata fields exist in a knowledge base.
        Returns: dict mapping metadata names to their IDs and types
        """
        # Check cache first
        if kb_id in self.metadata_cache:
            return self.metadata_cache[kb_id]

        # Get existing metadata fields
        response = self.dify_api.get_metadata_list(kb_id)
        existing_metadata = {}

        if response.status_code == 200:
            data = response.json()
            for field in data.get('doc_metadata', []):
                field_name = field.get('name')
                field_id = field.get('id')
                field_type = field.get('type')
                if field_name and field_id:
                    existing_metadata[field_name] = {'id': field_id, 'type': field_type}
            logger.info(f"  📋 Found {len(existing_metadata)} existing metadata fields")

        # Define required metadata fields
        required_fields = {
            'source_url': 'string',
            'crawl_date': 'time',
            'domain': 'string',
            'content_type': 'string',
            'processing_mode': 'string',
            'word_count': 'number'
        }

        # Create missing fields
        for field_name, field_type in required_fields.items():
            if field_name not in existing_metadata:
                logger.info(f"  ➕ Creating metadata field: {field_name} ({field_type})")
                response = self.dify_api.create_knowledge_metadata(kb_id, field_type, field_name)

                logger.debug(f"    Response status: {response.status_code}")
                logger.debug(f"    Response body: {response.text}")

                if response.status_code == 200:
                    field_data = response.json()
                    existing_metadata[field_name] = {
                        'id': field_data.get('id'),
                        'type': field_type
                    }
                    logger.info(f"    ✅ Created: {field_name} (ID: {field_data.get('id')})")
                elif response.status_code == 201:
                    # Some APIs return 201 for resource creation
                    field_data = response.json()
                    existing_metadata[field_name] = {
                        'id': field_data.get('id'),
                        'type': field_type
                    }
                    logger.info(f"    ✅ Created: {field_name} (ID: {field_data.get('id')})")
                else:
                    logger.error(f"    ❌ Failed to create {field_name} (status {response.status_code}): {response.text}")

        # Cache the metadata
        self.metadata_cache[kb_id] = existing_metadata
        return existing_metadata

    def prepare_document_metadata(self, url: str, processing_mode, word_count: int, metadata_fields: dict) -> list:
        """Prepare metadata values for a document.

        Args:
            url: Source URL
            processing_mode: ProcessingMode enum value
            word_count: Word count of content
            metadata_fields: dict of available metadata fields {name: {id, type}}

        Returns:
            List of metadata assignments [{"id": "...", "value": "...", "name": "..."}]
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')

        # Determine content type from URL
        path_lower = parsed_url.path.lower()
        if any(x in path_lower for x in ['/docs/', '/documentation/', '/guide/']):
            content_type = 'documentation'
        elif any(x in path_lower for x in ['/blog/', '/article/', '/news/']):
            content_type = 'article'
        elif any(x in path_lower for x in ['/tutorial/', '/how-to/']):
            content_type = 'tutorial'
        elif any(x in path_lower for x in ['/api/', '/reference/']):
            content_type = 'api_reference'
        else:
            content_type = 'general'

        # Build metadata list
        metadata_list = []
        current_time = int(datetime.now().timestamp())

        metadata_values = {
            'source_url': url,
            'crawl_date': current_time,
            'domain': domain,
            'content_type': content_type,
            'processing_mode': processing_mode.value if processing_mode else 'unknown',
            'word_count': word_count
        }

        for field_name, value in metadata_values.items():
            if field_name in metadata_fields:
                field_info = metadata_fields[field_name]
                metadata_list.append({
                    'id': field_info['id'],
                    'value': value,
                    'name': field_name
                })

        return metadata_list
    
    async def push_to_knowledge_base(self, kb_id: str, content_data: dict, url: str, processing_mode: ProcessingMode = None) -> Tuple[bool, str]:
        """Push content to specific knowledge base with duplicate detection and dual-mode support.
        Returns: (success, status_message)
        """
        # Normalize URL
        url = url.rstrip('/')

        markdown_content = content_data.get('description', '')
        title = content_data.get('title', 'Document')

        # Generate consistent document name based on URL (title is ignored)
        doc_name = self.generate_document_name(url, title)
        logger.info(f"  🔍 Document name for push: {doc_name}")

        # Load existing documents for this knowledge base
        existing_docs = await self.load_documents_for_knowledge_base(kb_id)

        # Check if document already exists
        if doc_name in existing_docs:
            logger.info(f"⏭️  Document already exists: {doc_name} (ID: {existing_docs[doc_name]})")
            return True, "skipped_existing"

        # Ensure metadata fields exist for this KB
        logger.info(f"  🏷️  Ensuring metadata fields exist...")
        metadata_fields = await self.ensure_metadata_fields(kb_id)

        # Determine configuration based on mode
        if self.enable_dual_mode and processing_mode:
            # Use dual-mode configuration
            dify_config = self.content_processor.get_dify_configuration(processing_mode)
            response = self.dify_api.create_document_from_text(
                dataset_id=kb_id,
                name=doc_name,
                text=markdown_content,
                custom_config=dify_config
            )
        else:
            # Use legacy configuration
            response = self.dify_api.create_document_from_text(
                dataset_id=kb_id,
                name=doc_name,
                text=markdown_content,
                use_parent_child=self.use_parent_child
            )

        if response.status_code == 200:
            # Update cache with new document
            doc_data = response.json()
            logger.info(f"  📄 Document creation response: {json.dumps(doc_data, indent=2)}")

            doc_id = doc_data.get('id') or doc_data.get('document', {}).get('id')
            if doc_id:
                existing_docs[doc_name] = doc_id
                logger.info(f"✅ Successfully pushed new document: {doc_name} (ID: {doc_id})")

                # Assign metadata to the document
                word_count = len(markdown_content.split())
                metadata_list = self.prepare_document_metadata(url, processing_mode, word_count, metadata_fields)

                if metadata_list:
                    logger.info(f"  🏷️  Assigning {len(metadata_list)} metadata fields...")
                    metadata_response = self.dify_api.assign_document_metadata(kb_id, doc_id, metadata_list)
                    if metadata_response.status_code == 200:
                        logger.info(f"    ✅ Metadata assigned successfully")
                        for meta in metadata_list:
                            if meta['name'] in ['source_url', 'domain', 'content_type', 'processing_mode']:
                                logger.info(f"      • {meta['name']}: {meta['value']}")
                    else:
                        logger.warning(f"    ⚠️  Failed to assign metadata: {metadata_response.text}")
            else:
                logger.warning(f"⚠️  Document created but no ID returned: {doc_name}")
                logger.info(f"  Response structure: {list(doc_data.keys())}")

            # Check indexing status if available
            indexing_status = doc_data.get('indexing_status') or doc_data.get('document', {}).get('indexing_status')
            if indexing_status:
                logger.info(f"  📊 Indexing status: {indexing_status}")

            return True, "created_new"
        else:
            logger.error(f"❌ Failed to push document: {response.status_code}")
            logger.error(f"  Error response: {response.text}")
            return False, "failed"
    
    
    def create_extraction_strategy(self, mode: ProcessingMode, extraction_model: str) -> LLMExtractionStrategy:
        """Create an extraction strategy based on the processing mode."""
        logger.debug(f"Creating strategy for mode: {mode.value if mode else 'None'}")
        logger.debug(f"Mode type: {type(mode)}")
        logger.debug(f"Mode == FULL_DOC: {mode == ProcessingMode.FULL_DOC}")
        logger.debug(f"Mode == PARAGRAPH: {mode == ProcessingMode.PARAGRAPH}")
        logger.debug(f"Mode is None: {mode is None}")
        
        # Get the appropriate prompt
        if mode == ProcessingMode.FULL_DOC:
            prompt_file = "prompts/extraction_prompt_full_doc.txt"
            fallback_prompt = self.content_processor._get_full_doc_prompt()
            logger.debug(f"Using full doc prompt")
        elif mode == ProcessingMode.PARAGRAPH:
            prompt_file = "prompts/extraction_prompt_parent_child.txt"
            fallback_prompt = self.content_processor._get_paragraph_prompt()
            logger.debug(f"Using paragraph (parent-child) prompt")
        else:
            # Default to legacy behavior
            if self.use_parent_child:
                prompt_file = "prompts/extraction_prompt_parent_child.txt"
                fallback_prompt = self.content_processor._get_paragraph_prompt()
                logger.debug(f"Using legacy parent-child prompt")
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
                logger.debug(f"Using legacy flexible prompt")

        # Try to load prompt from file
        try:
            with open(prompt_file, "r") as f:
                instruction = f.read()
            logger.debug(f"Loaded prompt from file: {prompt_file}")
            logger.debug(f"Prompt length: {len(instruction)} characters")
        except FileNotFoundError:
            instruction = fallback_prompt
            logger.warning(f"File not found: {prompt_file}, using fallback prompt")
            logger.debug(f"Fallback prompt length: {len(instruction)} characters")

        # Debug: Check what separators are in the instruction
        has_parent = "###PARENT_SECTION###" in instruction
        has_child = "###CHILD_SECTION###" in instruction
        has_section = "###SECTION###" in instruction
        has_break = "###SECTION_BREAK###" in instruction

        logger.debug(f"Prompt content analysis:")
        logger.debug(f"  Has ###PARENT_SECTION###: {has_parent}")
        logger.debug(f"  Has ###CHILD_SECTION###: {has_child}")
        logger.debug(f"  Has ###SECTION###: {has_section}")
        logger.debug(f"  Has ###SECTION_BREAK###: {has_break}")

        # Create extraction strategy
        logger.debug(f"Model: {extraction_model}")
        logger.debug(f"Schema: ResultSchema")
        logger.debug(f"Extraction type: schema")
        logger.debug(f"Temperature: 0.0")
        logger.debug(f"Max tokens: 32000")
        
        strategy = LLMExtractionStrategy(
            llm_config=LLMConfig(
                provider=extraction_model,
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
                "max_tokens": 32000
            }
        )

        logger.debug(f"Extraction strategy created successfully")
        return strategy
    
    async def process_crawled_content(self, content_data: dict, url: str, processing_mode: ProcessingMode = None) -> Tuple[bool, str]:
        """Process a single crawled content item through the complete workflow.
        Returns: (success, status)
        """
        try:
            description = content_data.get('description', '')

            # Display the processing mode that was already determined (no re-analysis)
            if self.enable_dual_mode and processing_mode:
                logger.info(f"  📋 Using processing mode: {processing_mode.value} (determined during extraction)")
            elif self.enable_dual_mode:
                logger.warning(f"  ⚠️  No processing mode provided, will use default for push")
            else:
                logger.info(f"  📋 Legacy mode: {'parent-child' if self.use_parent_child else 'flat'} chunking")
            
            # Handle knowledge base selection based on mode
            if self.knowledge_base_mode == 'manual' and self.selected_knowledge_base:
                # Manual mode: use the selected knowledge base
                kb_id = self.selected_knowledge_base
                
                # Get the KB name from our cache
                kb_name = None
                for name, id in self.knowledge_bases.items():
                    if id == kb_id:
                        kb_name = name
                        break
                
                if not kb_name:
                    # Try to get KB name from API
                    kb_name = f"Knowledge Base {kb_id}"

                logger.info(f"  📂 Using manually selected knowledge base: {kb_name}")

                # Manual mode - no categorization needed

            else:
                # Automatic mode: use smart categorization
                category = await self.categorize_content(description, url)

                logger.info(f"  📂 Category: {category}")

                # Ensure knowledge base exists
                kb_id = await self.ensure_knowledge_base_exists(category)
                if not kb_id:
                    logger.error(f"❌ Could not create or find knowledge base for category '{category}', trying fallback...")
                    # Try to create a generic fallback knowledge base
                    fallback_kb_id = await self.ensure_knowledge_base_exists("general")
                    if not fallback_kb_id:
                        logger.error(f"❌ Even fallback knowledge base failed, skipping content")
                        return False, "failed_kb_creation"
                    kb_id = fallback_kb_id
                    logger.info(f"✅ Using fallback knowledge base: general (ID: {kb_id})")
            
            # Push content to knowledge base with duplicate detection and mode
            success, status = await self.push_to_knowledge_base(kb_id, content_data, url, processing_mode)
            
            
            return success, status

        except Exception as e:
            logger.error(f"❌ Error processing content: {e}")
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
            logger.info("📋 Using cached knowledge bases from previous initialization")

        # Load checkpoint if exists (crash recovery)
        if self.enable_resilience and self.checkpoint.load():
            logger.info("🔄 RESUMING FROM CHECKPOINT")
            logger.info(f"   Previously processed: {len(self.checkpoint.state['processed_urls'])} URLs")
            logger.info(f"   Pending URLs: {len(self.checkpoint.state['pending_urls'])}")
            stats = self.checkpoint.get_statistics()
            logger.info(f"   Success: {stats['successful']}, Failed: {stats['failed']}, Skipped: {stats['skipped']}")
        else:
            # Initialize new checkpoint
            if self.enable_resilience:
                self.checkpoint.initialize(url, max_pages)
                logger.info("📝 Checkpoint system initialized")

        # Preload all documents for efficient duplicate checking
        await self.preload_all_documents()

        if not self.gemini_api_key:
            logger.warning("No GEMINI_API_KEY provided. Set GEMINI_API_KEY environment variable")
            return
        
        # Configure browser settings (keeping original logic)
        browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )
        
        # Print model configuration
        logger.info(f"🧠 Using models:")
        logger.info(f"  📝 Naming: {self.naming_model} (fast)")
        logger.info(f"  🔍 Extraction: {extraction_model} (smart)")
        if self.enable_dual_mode:
            if self.use_intelligent_mode:
                logger.info(f"  🤖 Intelligent mode enabled: Using LLM for content analysis")
                logger.info(f"     📊 Analysis model: {self.content_processor.analyzer.analysis_model}")
                logger.info(f"     🔍 Content value assessment (high/medium/low/skip)")
                logger.info(f"     📄 Single topic/tutorial/profile → Full Doc Mode")
                logger.info(f"     📚 Multi-topic/mixed content → Paragraph Mode")
                logger.info(f"     ⏭️  Low-value pages will be skipped")
            elif self.content_processor.use_word_threshold:
                logger.info(f"  🔀 Dual-mode enabled: Using WORD count threshold")
                logger.info(f"     📊 Threshold: {self.content_processor.word_threshold} words")
                logger.info(f"     📄 ≤ {self.content_processor.word_threshold} words → Full Doc Mode (sections)")
                logger.info(f"     📚 > {self.content_processor.word_threshold} words → Paragraph Mode (parent-child)")
            else:
                logger.info(f"  🔀 Dual-mode enabled: Using TOKEN count threshold")
                logger.info(f"     🎯 Threshold: {self.content_processor.token_threshold} tokens")
                logger.info(f"     📄 ≤ {self.content_processor.token_threshold} tokens → Full Doc Mode (sections)")
                logger.info(f"     📚 > {self.content_processor.token_threshold} tokens → Paragraph Mode (parent-child)")
        else:
            logger.info(f"  📄 Single mode: Using {'parent-child' if self.use_parent_child else 'flat'} chunking")
        
        # First, collect URLs without extraction to check for duplicates
        logger.info("\n🔍 Phase 1: Collecting URLs and checking for duplicates...")

        # Display knowledge base mode
        if self.knowledge_base_mode == 'manual' and self.selected_knowledge_base:
            kb_name = None
            for name, id in self.knowledge_bases.items():
                if id == self.selected_knowledge_base:
                    kb_name = name
                    break
            kb_display = kb_name or f"ID: {self.selected_knowledge_base}"
            logger.info(f"📚 Knowledge Base Mode: Manual - All content will be pushed to '{kb_display}'")
        else:
            logger.info(f"🤖 Knowledge Base Mode: Automatic - Content will be categorized intelligently")
        
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
            logger.info(f"🚀 Starting intelligent crawl workflow from: {url}")
            logger.info("📋 Configuration: Check Duplicates → Extract New → Organize in Knowledge Base")
            logger.info("-" * 80)
            
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
                            # Check if URL already processed in checkpoint
                            if self.enable_resilience and self.checkpoint.is_processed(page_result.url):
                                duplicate_urls.append(page_result.url)
                                logger.info(f"⏭️  [Page {crawled_count}] {page_result.url}")
                                logger.info(f"    Already processed (from checkpoint)")
                                continue

                            # Check if URL already exists in any knowledge base
                            exists, kb_id, doc_name = await self.check_url_exists(page_result.url)

                            if exists:
                                duplicate_urls.append(page_result.url)
                                if self.enable_resilience:
                                    self.checkpoint.mark_skipped(page_result.url)
                                logger.info(f"⏭️  [Page {crawled_count}] {page_result.url}")
                                logger.info(f"    Already exists as: '{doc_name}' in KB: {kb_id}")
                            else:
                                urls_to_process.append(page_result.url)
                                if self.enable_resilience:
                                    self.checkpoint.add_pending([page_result.url])
                                logger.info(f"✅ [Page {crawled_count}] {page_result.url}")
                                logger.info(f"    Will be saved as: '{doc_name}' - New URL to process")


            except Exception as e:
                logger.error(f"\nError during URL collection: {e}")

            # Phase 1 Summary
            logger.info(f"\n📄 Phase 1 Complete:")
            logger.info(f"  Total URLs found: {crawled_count}")
            logger.info(f"  Duplicate URLs skipped: {len(duplicate_urls)}")
            logger.info(f"  New URLs to process: {len(urls_to_process)}")

            if not urls_to_process:
                logger.info("\n✅ All URLs already exist in knowledge base. No new content to extract!")
                return

            # Phase 2: Extract content only for new URLs
            logger.info(f"\n🔍 Phase 2: Extracting content for {len(urls_to_process)} new URLs...")
            logger.info("-" * 80)
            
            extracted_files = []
            workflow_results = []
            extraction_failures = 0
            
            # Process each new URL with dynamic extraction strategy
            # We'll create extraction strategy per URL if dual mode is enabled
            
            # Process each new URL
            for idx, process_url in enumerate(urls_to_process, 1):
                logger.info(f"\n[{idx}/{len(urls_to_process)}] Processing: {process_url}")

                retry_count = 0
                max_retries = 2
                extraction_successful = False

                while retry_count <= max_retries and not extraction_successful:
                    try:
                        if retry_count > 0:
                            logger.info(f"  🔄 Retry attempt {retry_count}/{max_retries}...")
                            await asyncio.sleep(2)  # Brief delay before retry

                        # First, get the raw content to analyze its length if dual mode is enabled
                        if self.enable_dual_mode:
                            logger.info(f"  🔍 Dual-mode enabled: Getting raw content for analysis...")
                            # Get content without extraction first
                            raw_config = CrawlerRunConfig(
                                extraction_strategy=None,
                                cache_mode=CacheMode.BYPASS
                            )
                            raw_result = await crawler.arun(url=process_url, config=raw_config)

                            logger.info(f"  📄 Raw crawl result:")
                            logger.info(f"    Success: {raw_result.success}")
                            logger.info(f"    Has markdown: {bool(getattr(raw_result, 'markdown', None))}")
                            logger.info(f"    Markdown length: {len(getattr(raw_result, 'markdown', '')) if getattr(raw_result, 'markdown', None) else 0}")

                            if raw_result.success and raw_result.markdown:
                                # Determine processing mode based on content
                                logger.info(f"  🔍 Mode selection process:")
                                
                                # Check for manual mode first
                                if self.manual_mode:
                                    if self.manual_mode == 'full_doc':
                                        processing_mode = ProcessingMode.FULL_DOC
                                        logger.info(f"  ✋ Manual mode: FULL DOC")
                                    else:
                                        processing_mode = ProcessingMode.PARAGRAPH
                                        logger.info(f"  ✋ Manual mode: PARAGRAPH")
                                    mode_analysis = {'manual_mode': True, 'selection_reason': f'Manual override: {self.manual_mode}'}
                                # Use intelligent mode if enabled
                                elif self.use_intelligent_mode:
                                    try:
                                        logger.info(f"  🤖 Running intelligent content analysis...")
                                        processing_mode, mode_analysis = await self.content_processor.determine_processing_mode_intelligent(
                                            raw_result.markdown, process_url
                                        )

                                        # Check if we should skip this page
                                        if mode_analysis.get('skip', False):
                                            logger.info(f"  ⏭️  Skipping page: {mode_analysis.get('skip_reason', 'Low value content')}")
                                            logger.info(f"     Content value: {mode_analysis.get('content_value', 'low')}")
                                            continue  # Skip to next URL

                                        logger.info(f"  📊 Intelligent analysis results:")
                                        logger.info(f"     🎯 Content value: {mode_analysis.get('content_value', 'unknown')}")
                                        logger.info(f"     📋 Structure: {mode_analysis.get('content_structure', 'unknown')}")
                                        logger.info(f"     📝 Type: {mode_analysis.get('content_type', 'unknown')}")
                                        logger.info(f"     🔍 Main topics: {', '.join(mode_analysis.get('main_topics', []))}")
                                        logger.info(f"  📄 Selected mode: {processing_mode.value}")
                                        # Show the AI's reasoning if available, otherwise show selection reason
                                        reason = mode_analysis.get('mode_reason') or mode_analysis.get('selection_reason', '')
                                        if reason:
                                            logger.info(f"     ℹ️  {reason}")
                                        
                                    except Exception as e:
                                        logger.warning(f"  ⚠️  Intelligent analysis failed: {e}")
                                        logger.info(f"  🔄 Falling back to threshold-based mode selection...")
                                        # Fall back to regular mode selection
                                        url_suggests_full_doc = self.content_processor.should_use_full_doc_for_url(process_url)
                                        if url_suggests_full_doc:
                                            processing_mode = ProcessingMode.FULL_DOC
                                            logger.info(f"  📄 URL pattern suggests full doc mode")
                                        else:
                                            processing_mode, mode_analysis = self.content_processor.determine_processing_mode(raw_result.markdown)
                                            logger.info(f"  📊 Threshold-based analysis:")
                                            logger.info(f"     📝 Word count: {mode_analysis.get('word_count', 0):,} words")
                                            logger.info(f"     🎯 Token count: {mode_analysis.get('token_count', 0):,} tokens")
                                            logger.info(f"  📄 Selected mode: {processing_mode.value}")
                                            logger.info(f"     ℹ️  {mode_analysis.get('selection_reason', '')}")
                                else:
                                    # Regular threshold-based mode selection
                                    url_suggests_full_doc = self.content_processor.should_use_full_doc_for_url(process_url)
                                    logger.info(f"    URL suggests full doc: {url_suggests_full_doc}")

                                    if url_suggests_full_doc:
                                        processing_mode = ProcessingMode.FULL_DOC
                                        logger.info(f"  📄 URL pattern suggests full doc mode")
                                        logger.info(f"    Final selected mode: {processing_mode.value}")
                                    else:
                                        processing_mode, mode_analysis = self.content_processor.determine_processing_mode(raw_result.markdown)
                                        logger.info(f"  📊 Content analysis:")
                                        logger.info(f"     📝 Word count: {mode_analysis.get('word_count', 0):,} words")
                                        logger.info(f"     🎯 Token count: {mode_analysis.get('token_count', 0):,} tokens")
                                        logger.info(f"     📏 Using {mode_analysis.get('threshold_type', 'word')} threshold")
                                        logger.info(f"     🔍 Decision: {mode_analysis.get('decision', '')}")
                                        logger.info(f"  📄 Selected mode: {processing_mode.value}")
                                        logger.info(f"     ℹ️  {mode_analysis.get('selection_reason', '')}")

                                # Create appropriate extraction strategy
                                logger.info(f"  🛠️  Creating extraction strategy for {processing_mode.value} mode...")
                                extraction_strategy = self.create_extraction_strategy(processing_mode, extraction_model)
                                extraction_config = CrawlerRunConfig(
                                    extraction_strategy=extraction_strategy,
                                    cache_mode=CacheMode.BYPASS
                                )
                            else:
                                logger.warning(f"  ⚠️  Failed to get raw content for analysis")
                                logger.info(f"    Raw result success: {raw_result.success}")
                                logger.info(f"    Raw result markdown: {bool(getattr(raw_result, 'markdown', None))}")
                                if hasattr(raw_result, 'error_message'):
                                    logger.error(f"    Error: {raw_result.error_message}")
                                logger.info(f"    Using default mode...")
                                # Fall back to default strategy
                                processing_mode = ProcessingMode.PARAGRAPH if self.use_parent_child else None
                                extraction_strategy = self.create_extraction_strategy(processing_mode, extraction_model)
                                extraction_config = CrawlerRunConfig(
                                    extraction_strategy=extraction_strategy,
                                    cache_mode=CacheMode.BYPASS
                                )
                        else:
                            # Legacy mode - create extraction strategy based on use_parent_child
                            processing_mode = ProcessingMode.PARAGRAPH if self.use_parent_child else None
                            extraction_strategy = self.create_extraction_strategy(processing_mode, extraction_model)
                            extraction_config = CrawlerRunConfig(
                                extraction_strategy=extraction_strategy,
                                cache_mode=CacheMode.BYPASS
                            )
                        
                        # Now extract with the appropriate strategy
                        result = await crawler.arun(url=process_url, config=extraction_config)

                        # Enhanced logging for debugging
                        logger.info(f"  🔍 Crawl result details:")
                        logger.info(f"    Success: {result.success}")
                        logger.info(f"    Has extracted_content: {bool(result.extracted_content)}")
                        logger.info(f"    Has markdown: {bool(getattr(result, 'markdown', None))}")
                        logger.info(f"    Has cleaned_html: {bool(getattr(result, 'cleaned_html', None))}")

                        if hasattr(result, 'error_message') and result.error_message:
                            logger.error(f"    Error message: {result.error_message}")

                        if result.extracted_content:
                            logger.info(f"    Extracted content type: {type(result.extracted_content)}")
                            if isinstance(result.extracted_content, str):
                                logger.info(f"    Extracted content length: {len(result.extracted_content)} chars")
                                logger.info(f"    Extracted content preview: {result.extracted_content[:200]}...")
                            else:
                                logger.info(f"    Extracted content: {result.extracted_content}")
                        
                        if result.success and result.extracted_content:
                            # Parse extracted data with enhanced error handling
                            try:
                                if isinstance(result.extracted_content, str):
                                    logger.info(f"  📝 Parsing JSON string...")
                                    extracted_data = json.loads(result.extracted_content)
                                else:
                                    logger.info(f"  📝 Using direct extracted content...")
                                    extracted_data = result.extracted_content

                                logger.info(f"  📊 Parsed data type: {type(extracted_data)}")

                                if isinstance(extracted_data, list):
                                    logger.info(f"  📋 List with {len(extracted_data)} items")
                                    extracted_data = extracted_data[0] if extracted_data else {}

                                logger.info(f"  🔑 Final data keys: {list(extracted_data.keys()) if isinstance(extracted_data, dict) else 'Not a dict'}")
                                
                                if extracted_data and extracted_data.get('description'):
                                    logger.info(f"  ✅ Valid description found: {len(extracted_data.get('description', ''))} chars")
                                    # Save JSON
                                    url_filename = process_url.replace("https://", "").replace("http://", "")
                                    url_filename = url_filename.replace("/", "_").replace("?", "_").replace(":", "_")
                                    if len(url_filename) > 100:
                                        url_filename = url_filename[:100]

                                    json_file = Path(output_dir) / f"{url_filename}.json"
                                    with open(json_file, "w", encoding="utf-8") as f:
                                        json.dump(extracted_data, f, indent=2, ensure_ascii=False)

                                    extracted_files.append(str(json_file))
                                    logger.info(f"  💾 Saved: {json_file}")

                                    # Display summary
                                    logger.info(f"  📄 Title: {extracted_data.get('title', 'N/A')}")
                                    desc = extracted_data.get('description', '')
                                    desc_length = len(desc)
                                    # Display summary based on actual content structure
                                    if '###PARENT_SECTION###' in desc:
                                        parent_count = desc.count('###PARENT_SECTION###')
                                        child_count = desc.count('###CHILD_SECTION###')
                                        logger.info(f"  📝 Description: {desc_length} characters in {parent_count} parent chunks with {child_count} child chunks")
                                    elif '###SECTION###' in desc:
                                        section_count = desc.count('###SECTION###')
                                        logger.info(f"  📝 Description: {desc_length} characters in {section_count} sections (full doc mode)")
                                    elif '###SECTION_BREAK###' in desc:
                                        chunk_count = desc.count('###SECTION_BREAK###') + 1
                                        logger.info(f"  📝 Description: {desc_length} characters in {chunk_count} chunks")
                                    else:
                                        # No recognized markers
                                        logger.info(f"  📝 Description: {desc_length} characters")
                                    
                                    # Process through workflow (pass the processing mode that was determined)
                                    workflow_success, status = await self.process_crawled_content(
                                        extracted_data, process_url, processing_mode
                                    )

                                    # Track in checkpoint and failure queue
                                    if self.enable_resilience:
                                        if workflow_success:
                                            self.checkpoint.mark_processed(process_url, success=True)
                                        else:
                                            self.checkpoint.mark_failed(process_url, f"Workflow status: {status}")
                                            self.failure_queue.add(process_url, f"Workflow failed: {status}")

                                        # Save checkpoint every 5 URLs
                                        if len(self.checkpoint.state['processed_urls']) % 5 == 0:
                                            self.checkpoint.save()

                                    workflow_results.append({
                                        'url': process_url,
                                        'title': extracted_data.get('title', 'Untitled'),
                                        'success': workflow_success,
                                        'status': status,
                                        'category': await self.categorize_content(desc, process_url)
                                    })

                                    extraction_successful = True
                                else:
                                    logger.warning(f"  ⚠️  No valid content extracted")
                                    logger.info(f"    Reason: Missing description field or empty data")
                                    logger.info(f"    Data structure: {extracted_data}")
                                    if retry_count < max_retries:
                                        retry_count += 1
                                    else:
                                        extraction_failures += 1
                                        break

                            except json.JSONDecodeError as e:
                                logger.error(f"  ❌ JSON parsing error: {e}")
                                logger.error(f"    Raw content: {result.extracted_content[:500]}...")
                                if retry_count < max_retries:
                                    retry_count += 1
                                else:
                                    extraction_failures += 1
                                    break
                            except Exception as e:
                                logger.error(f"  ❌ Extraction parsing error: {e}")
                                import traceback
                                traceback.print_exc()
                                if retry_count < max_retries:
                                    retry_count += 1
                                else:
                                    extraction_failures += 1
                                    break
                        else:
                            logger.warning(f"  ⚠️  Extraction failed: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
                            if retry_count < max_retries:
                                retry_count += 1
                            else:
                                extraction_failures += 1
                                break

                    except Exception as e:
                        logger.error(f"  ❌ Error: {e}")
                        if retry_count < max_retries:
                            retry_count += 1
                        else:
                            extraction_failures += 1
                            # Track extraction failure
                            if self.enable_resilience:
                                self.checkpoint.mark_failed(process_url, f"Extraction error: {str(e)}")
                                self.failure_queue.add(process_url, f"Extraction failed after {max_retries} retries: {str(e)}")
                            break
            
            # Final summary
            logger.info("\n" + "=" * 80)
            logger.info("🎯 INTELLIGENT CRAWL WORKFLOW SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Total URLs discovered: {crawled_count}")
            logger.info(f"Duplicate URLs skipped (saved tokens): {len(duplicate_urls)}")
            logger.info(f"New URLs processed: {len(urls_to_process)}")
            logger.info(f"Extraction failures: {extraction_failures}")
            logger.info(f"Total documents saved: {len(extracted_files)}")

            if workflow_results:
                successful = sum(1 for r in workflow_results if r['success'])
                created_new = sum(1 for r in workflow_results if r.get('status') == 'created_new')
                skipped_existing = sum(1 for r in workflow_results if r.get('status') == 'skipped_existing')
                failed = sum(1 for r in workflow_results if not r['success'])

                logger.info(f"Knowledge base operations: {successful}/{len(workflow_results)} successful")
                logger.info(f"  ✅ New documents created: {created_new}")
                logger.info(f"  ⏭️  Existing documents skipped: {skipped_existing}")
                logger.info(f"  ❌ Failed operations: {failed}")

                # Show knowledge bases created/used
                logger.info(f"\n📚 Knowledge bases: {len(self.knowledge_bases)}")
                for name, kb_id in self.knowledge_bases.items():
                    logger.info(f"  • {name} (ID: {kb_id})")

                # Show documents cached
                total_docs_cached = sum(len(docs) for docs in self.document_cache.values())
                logger.info(f"\n📄 Total documents tracked: {total_docs_cached}")

            # Save final checkpoint and export failure reports
            if self.enable_resilience:
                logger.info("\n🛡️  RESILIENCE SUMMARY")
                logger.info("=" * 80)

                # Final checkpoint save
                self.checkpoint.save()
                stats = self.checkpoint.get_statistics()
                logger.info(f"✅ Checkpoint saved:")
                logger.info(f"   Processed: {len(self.checkpoint.state['processed_urls'])} URLs")
                logger.info(f"   Success: {stats['successful']}")
                logger.info(f"   Failed: {stats['failed']}")
                logger.info(f"   Skipped: {stats['skipped']}")

                # Export failure queue if there are failures
                if len(self.failure_queue.failures) > 0:
                    self.failure_queue.export_report("failed_urls_report.json")
                    logger.info(f"\n❌ {len(self.failure_queue.failures)} failed URLs exported to: failed_urls_report.json")

                    # Show retryable failures
                    retryable = self.failure_queue.get_retryable(max_retries=3)
                    if retryable:
                        logger.info(f"   {len(retryable)} URLs can be retried")
                        logger.info(f"   Run workflow again to retry failed URLs")
                else:
                    logger.info(f"\n✅ No failures - all URLs processed successfully!")

            # Note: Token usage tracking would need to aggregate across multiple strategies in dual mode


# Example usage and main function
async def main():
    """Example usage of the CrawlWorkflow with dual-model setup."""
    load_dotenv(override=True)
    
    # Initialize workflow with dual-model and dual-mode configuration
    workflow = CrawlWorkflow(
        dify_base_url=os.getenv('DIFY_BASE_URL', 'http://localhost:8088'),
        dify_api_key=os.getenv('DIFY_API_KEY'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_dual_mode=True,  # Enable automatic mode selection based on content length
        word_threshold=4000,    # Switch to full doc mode for content under 4000 words
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