import json
from typing import Dict, Tuple
from enum import Enum
import asyncio
import aiohttp

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
        self.custom_llm_api_key = custom_llm_api_key or llm_api_key
        
    async def analyze_content(self, url: str, content: str) -> Dict[str, any]:
        """
        Analyze content using LLM to determine value and structure.
        
        Returns:
            Dict with analysis results including value, structure, and mode recommendation
        """
        # Create analysis prompt
        analysis_prompt = self._create_analysis_prompt()
        
        # Prepare content for analysis (limit to 5000 chars)
        content_sample = content[:5000] if len(content) > 5000 else content
        
        # Create the full prompt
        full_prompt = f"{analysis_prompt}\n\nURL: {url}\n\nCONTENT:\n{content_sample}\n{'... [content truncated]' if len(content) > 5000 else ''}"
        
        try:
            # Use direct API call for Gemini
            if "gemini" in self.analysis_model.lower():
                result = await self._call_gemini_api(full_prompt)
            else:
                # For other models, use custom endpoint if provided
                if self.custom_llm_base_url:
                    result = await self._call_custom_llm(full_prompt)
                else:
                    # Fallback to Gemini if no custom endpoint
                    result = await self._call_gemini_api(full_prompt)
            
            if result:
                # Parse the JSON response
                analysis = self._parse_llm_response(result)
                
                # Debug: Print what the LLM returned
                print(f"  🤖 LLM Analysis Response:")
                print(f"     Structure: {analysis.get('content_structure', 'unknown')}")
                print(f"     Recommended Mode: {analysis.get('recommended_mode', 'NOT PROVIDED')}")
                print(f"     Mode Reason: {analysis.get('mode_reason', 'No reason provided')}")
                
                # Add derived insights
                analysis['should_process'] = analysis.get('content_value') in ['high', 'medium']
                analysis['url'] = url
                
                return analysis
            else:
                raise Exception("No response from LLM")
                
        except Exception as e:
            print(f"  ⚠️  AI analysis failed: {str(e)}")
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
    
    async def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API directly."""
        model_name = self.analysis_model.split("/")[-1] if "/" in self.analysis_model else "gemini-1.5-flash"
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        
        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': self.llm_api_key
        }
        
        # Add JSON output instruction
        json_prompt = prompt + "\n\nProvide your response in valid JSON format only, with no additional text or markdown formatting."
        
        data = {
            "contents": [{
                "parts": [{
                    "text": json_prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1000,
                "topK": 40,
                "topP": 0.95
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    # Extract text from Gemini response
                    if 'candidates' in result and len(result['candidates']) > 0:
                        return result['candidates'][0]['content']['parts'][0]['text']
                else:
                    error_text = await response.text()
                    raise Exception(f"Gemini API error: {response.status} - {error_text}")
        
        return None
    
    async def _call_custom_llm(self, prompt: str) -> str:
        """Call custom LLM endpoint."""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.custom_llm_api_key}'
        }
        
        data = {
            "prompt": prompt,
            "model": self.analysis_model,
            "temperature": 0.2,
            "max_tokens": 1000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.custom_llm_base_url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    # Extract response based on common formats
                    if 'response' in result:
                        return result['response']
                    elif 'text' in result:
                        return result['text']
                    elif 'content' in result:
                        return result['content']
                    else:
                        return json.dumps(result)
                else:
                    error_text = await response.text()
                    raise Exception(f"Custom LLM API error: {response.status} - {error_text}")
        
        return None
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, any]:
        """Parse LLM response to extract JSON."""
        # Try to extract JSON from the response
        import re
        
        # First try direct JSON parsing
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON using a more robust pattern
        # This looks for content between outermost braces
        brace_count = 0
        start_idx = -1
        end_idx = -1
        
        for i, char in enumerate(response_text):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    end_idx = i + 1
                    break
        
        if start_idx != -1 and end_idx != -1:
            try:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON between code blocks
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass
        
        raise ValueError("Could not parse JSON from LLM response")
    
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

Provide your analysis in this exact JSON format:
{
    "content_value": "high|medium|low|skip",
    "value_reason": "Brief explanation",
    "content_structure": "single_topic|multi_topic|reference|list|mixed",
    "structure_reason": "Brief explanation", 
    "main_topics": ["topic1", "topic2"],
    "recommended_mode": "full_doc|paragraph",
    "mode_reason": "Detailed explanation of why this mode is recommended",
    "content_type": "Type of content",
    "has_code": false,
    "is_navigational": false
}"""
    
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
        
        # Get content structure
        structure = analysis.get('content_structure', 'mixed')
        
        # Use the LLM's recommendation if provided, otherwise determine from structure
        mode = analysis.get('recommended_mode')
        
        # If no mode recommendation or inconsistent, determine from structure
        if not mode or (structure == 'single_topic' and mode != 'full_doc'):
            if structure in ['single_topic', 'reference']:
                mode = 'full_doc'
                reason = f"Content is {structure} - keeping full document for complete context"
            else:
                mode = 'paragraph'
                reason = f"Content is {structure} - using paragraph mode for chunked retrieval"
        else:
            reason = analysis.get('mode_reason', 'Based on content structure analysis')
        
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