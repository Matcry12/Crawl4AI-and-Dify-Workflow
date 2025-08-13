import json
from typing import Dict, Tuple
from enum import Enum
import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy


class ContentValue(Enum):
    HIGH = "high"           # Valuable for RAG/AI
    MEDIUM = "medium"       # Some value
    LOW = "low"             # Little value
    SKIP = "skip"           # Should not be processed

class ContentStructure(Enum):
    SINGLE_TOPIC = "single_topic"      # Tutorial, guide, profile - use full_doc
    MULTI_TOPIC = "multi_topic"        # Multiple topics - use paragraph
    REFERENCE = "reference"            # API docs, specs - use full_doc
    LIST = "list"                      # Lists, indexes - use paragraph
    MIXED = "mixed"                    # Mixed content - use paragraph

class IntelligentContentAnalyzer:
    def __init__(self, llm_api_key: str, analysis_model: str = "gemini/gemini-1.5-flash", custom_llm_base_url: str = None, custom_llm_api_key: str = None):
        """
        Initialize the intelligent content analyzer.
        
        Args:
            llm_api_key: API key for LLM
            analysis_model: Model to use for quick content analysis (fast & cheap)
            custom_llm_base_url: Custom LLM endpoint URL (optional)
            custom_llm_api_key: Custom LLM API key (optional)
        """
        self.llm_api_key = llm_api_key
        self.analysis_model = analysis_model
        self.custom_llm_base_url = custom_llm_base_url
        self.custom_llm_api_key = custom_llm_api_key
        
    async def analyze_content(self, url: str, content: str) -> Dict[str, any]:
        """
        Analyze content using LLM to determine value and structure.
        
        Returns:
            Dict with analysis results including value, structure, and mode recommendation
        """
        # Create analysis prompt
        analysis_prompt = self._create_analysis_prompt()
        
        # Configure LLM extraction for analysis
        if self.custom_llm_base_url:
            # Use custom LLM configuration
            llm_config = LLMConfig(
                provider="custom",  # Use custom provider
                api_token=self.custom_llm_api_key or self.llm_api_key,
                base_url=self.custom_llm_base_url,
                extra_args={
                    "model": self.analysis_model  # Pass model name for custom endpoint
                }
            )
        else:
            # Use standard provider
            llm_config = LLMConfig(
                provider=self.analysis_model,
                api_token=self.llm_api_key
            )
        
        # Define schema for structured analysis
        analysis_schema = {
            "type": "object",
            "properties": {
                "content_value": {
                    "type": "string",
                    "enum": ["high", "medium", "low", "skip"],
                    "description": "Value of content for AI/RAG systems"
                },
                "value_reason": {
                    "type": "string",
                    "description": "Brief explanation of value assessment"
                },
                "content_structure": {
                    "type": "string",
                    "enum": ["single_topic", "multi_topic", "reference", "list", "mixed"],
                    "description": "Structure type of the content"
                },
                "structure_reason": {
                    "type": "string",
                    "description": "Brief explanation of structure assessment"
                },
                "main_topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Main topics covered"
                },
                "recommended_mode": {
                    "type": "string",
                    "enum": ["full_doc", "paragraph"],
                    "description": "Recommended processing mode"
                },
                "mode_reason": {
                    "type": "string",
                    "description": "Detailed explanation of why this mode is recommended. Be specific about whether content is single-topic (needs full context) or multi-topic (can be chunked). Explain how the content structure affects RAG retrieval."
                },
                "content_type": {
                    "type": "string",
                    "description": "Type of content (tutorial, profile, documentation, etc.)"
                },
                "has_code": {
                    "type": "boolean",
                    "description": "Whether content contains code examples"
                },
                "is_navigational": {
                    "type": "boolean",
                    "description": "Whether this is mainly a navigation/index page"
                }
            },
            "required": ["content_value", "content_structure", "recommended_mode"]
        }
        
        # Create extraction strategy
        extraction_strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            schema=analysis_schema,
            extraction_type="schema",
            instruction=analysis_prompt,
            chunk_token_threshold=100000,  # Don't chunk for analysis
            input_format="markdown",
            extra_args={
                "temperature": 0.2,  # Low temperature for consistent analysis
                "max_tokens": 1000   # Small response for quick analysis
            }
        )
        
        # Analyze content
        browser_config = BrowserConfig(headless=True, verbose=False)
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Create a simple markdown representation for analysis
            analysis_input = f"""
URL: {url}

CONTENT:
{content[:5000]}  # Limit to first 5000 chars for analysis
{'... [content truncated]' if len(content) > 5000 else ''}
"""
            
            # Run analysis
            config = CrawlerRunConfig(
                extraction_strategy=extraction_strategy,
                cache_mode=CacheMode.BYPASS
            )
            
            # We need to pass the content directly, so we'll use a data URL
            import base64
            data_url = f"data:text/plain;base64,{base64.b64encode(analysis_input.encode()).decode()}"
            
            # Add timeout to prevent hanging
            try:
                result = await asyncio.wait_for(
                    crawler.arun(url=data_url, config=config),
                    timeout=30.0  # 30 second timeout
                )
            except asyncio.TimeoutError:
                print(f"  ⚠️  Analysis timeout after 30 seconds")
                raise Exception("Content analysis timed out")
            
            if result.success and result.extracted_content:
                try:
                    analysis = json.loads(result.extracted_content)
                    
                    # Add derived insights
                    analysis['should_process'] = analysis.get('content_value') in ['high', 'medium']
                    analysis['url'] = url
                    
                    
                    return analysis
                except json.JSONDecodeError:
                    print(f"  ⚠️  Failed to parse AI analysis response")
                    if result.extracted_content:
                        print(f"  📝 Raw AI response (first 500 chars): {result.extracted_content[:500]}")
            else:
                # Simple fallback message
                print(f"  ⚠️  AI analysis failed - using fallback")
                if not result.success:
                    print(f"     Result not successful")
                    if hasattr(result, 'error_message'):
                        print(f"     Error: {result.error_message}")
                if not result.extracted_content:
                    print(f"     No extracted content from AI")
                    
                # Fallback analysis
                return {
                    'content_value': 'medium',
                    'value_reason': 'Unable to analyze, defaulting to medium value',
                    'content_structure': 'mixed',
                    'structure_reason': 'Unable to determine structure',
                    'recommended_mode': 'paragraph',
                    'mode_reason': 'Default to paragraph mode for safety',
                    'should_process': True,
                    'url': url,
                    'error': 'Analysis failed'
                }
    
    def _create_analysis_prompt(self) -> str:
        """Create the prompt for content analysis."""
        return """You are an expert content analyzer for RAG (Retrieval-Augmented Generation) systems.

IMPORTANT: Focus on the MAIN ARTICLE CONTENT, ignoring navigation menus, sidebars, footers, and ads.

Analyze the provided content and determine:

1. CONTENT VALUE for AI/RAG:
   - HIGH: Tutorials, documentation, guides, technical content, educational material, unique information
   - MEDIUM: General articles, news, reviews with some informational value  
   - LOW: Navigation pages, brief announcements, minimal content
   - SKIP: Error pages, login pages, pure navigation, advertisements, cookie notices

2. CONTENT STRUCTURE - Look at the MAIN CONTENT ONLY:
   - SINGLE_TOPIC: The main article/content is about ONE subject
     * Wiki page about Brontosaurus (even with sections like History, Habitat, Diet) = SINGLE_TOPIC
     * Tutorial about Python (with multiple chapters/sections) = SINGLE_TOPIC
     * Product documentation (with features, setup, usage sections) = SINGLE_TOPIC
     * ANY Wikipedia-style article about one thing = SINGLE_TOPIC
   
   - MULTI_TOPIC: The page contains MULTIPLE SEPARATE articles or very different topics
     * Homepage with different news articles = MULTI_TOPIC
     * Blog index with multiple unrelated posts = MULTI_TOPIC
     * Page with "Python Tutorial" AND "Cooking Recipes" as separate articles = MULTI_TOPIC
     * Documentation hub covering completely different products = MULTI_TOPIC

3. RECOMMENDED MODE:
   - FULL_DOC: Use when the main content is about ONE topic
     * Wiki article about an animal/person/place/thing = FULL_DOC
     * Tutorial or guide (even with many sections) = FULL_DOC
     * Documentation for one product/API = FULL_DOC
     * Blog post about one subject = FULL_DOC
   
   - PARAGRAPH: Use ONLY when page has MULTIPLE DISTINCT topics/articles
     * Homepage with different article previews = PARAGRAPH
     * Search results page = PARAGRAPH
     * Category page listing different items = PARAGRAPH

DECISION RULE:
Ask yourself: "Is this page's MAIN CONTENT about ONE thing or MULTIPLE different things?"
- ONE thing (even with subsections like History, Features, Usage) → FULL_DOC
- MULTIPLE different things → PARAGRAPH

CRITICAL: 
- Different sections about the SAME topic (e.g., Habitat and Diet of Brontosaurus) = STILL ONE TOPIC = FULL_DOC
- Navigation elements don't count as "different topics"
- Focus on the actual article/content, not the page structure

Analyze the content and provide structured assessment."""
    
    def determine_processing_mode(self, analysis: Dict[str, any]) -> Tuple[str, str]:
        """
        Determine the processing mode based on analysis.
        
        Returns:
            Tuple of (mode, reason)
        """
        # First check if we should skip
        if not analysis.get('should_process', True):
            skip_reason = f"Content value is {analysis.get('content_value', 'low')}"
            return "skip", skip_reason
        
        # Use the LLM's recommendation
        mode = analysis.get('recommended_mode', 'paragraph')
        reason = analysis.get('mode_reason', 'Based on content structure analysis')
        
        # Additional logic based on content structure
        structure = analysis.get('content_structure', 'mixed')
        
        # Additional validation based on structure
        if structure in ['single_topic', 'reference']:
            if mode != 'full_doc':
                reason += f" (Note: {structure} structure typically uses full_doc)"
        elif structure in ['multi_topic', 'list', 'mixed']:
            if mode != 'paragraph':
                reason += f" (Note: {structure} structure typically uses paragraph)"
        
        return mode, reason
    
    def should_skip_page(self, analysis: Dict[str, any]) -> Tuple[bool, str]:
        """
        Determine if a page should be skipped.
        
        Returns:
            Tuple of (should_skip, reason)
        """
        value = analysis.get('content_value', 'medium')
        
        if value == 'skip':
            return True, analysis.get('value_reason', 'Page marked as skip value')
        elif value == 'low' and analysis.get('is_navigational', False):
            return True, "Low value navigational page"
        else:
            return False, "Page has sufficient value for processing"

