import tiktoken
from typing import Dict, Tuple, Optional, List
from enum import Enum
from intelligent_content_analyzer import IntelligentContentAnalyzer, ContentValue, ContentStructure

class ProcessingMode(Enum):
    PARAGRAPH = "paragraph"  # Parent-child hierarchical mode for long content
    FULL_DOC = "full_doc"    # Full document mode for shorter content
    
class ContentProcessor:
    def __init__(self, 
                 word_threshold: int = 4000,  # Default word count threshold for mode selection
                 token_threshold: int = 8000,  # Default token count threshold (optional)
                 use_word_threshold: bool = True,  # Toggle between word/token threshold
                 use_intelligent_mode: bool = False,  # Use LLM for intelligent mode selection
                 llm_api_key: Optional[str] = None,  # API key for intelligent mode
                 analysis_model: str = "gemini/gemini-1.5-flash",  # Model for content analysis
                 custom_llm_base_url: Optional[str] = None,  # Custom LLM endpoint for analysis
                 custom_llm_api_key: Optional[str] = None,  # Custom LLM API key for analysis
                 paragraph_parent_tokens: int = 4000,
                 paragraph_child_tokens: int = 4000,
                 full_doc_chunk_tokens: int = 2000,
                 full_doc_max_chunks: int = 5):
        """
        Initialize content processor with configurable thresholds.
        
        Args:
            word_threshold: Word count threshold to decide between modes
            token_threshold: Token count threshold (used if use_word_threshold=False)
            use_word_threshold: If True, use word count; if False, use token count
            use_intelligent_mode: If True, use LLM to analyze content structure
            llm_api_key: API key for LLM (required if use_intelligent_mode=True)
            analysis_model: Model to use for content analysis
            paragraph_parent_tokens: Max tokens for parent chunks in paragraph mode
            paragraph_child_tokens: Max tokens for child chunks in paragraph mode
            full_doc_chunk_tokens: Max tokens per chunk in full doc mode
            full_doc_max_chunks: Max number of chunks for full doc mode
        """
        self.word_threshold = word_threshold
        self.token_threshold = token_threshold
        self.use_word_threshold = use_word_threshold
        self.use_intelligent_mode = use_intelligent_mode
        self.paragraph_parent_tokens = paragraph_parent_tokens
        self.paragraph_child_tokens = paragraph_child_tokens
        self.full_doc_chunk_tokens = full_doc_chunk_tokens
        self.full_doc_max_chunks = full_doc_max_chunks
        
        # Initialize tokenizer (using cl100k_base which is used by GPT-4)
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Initialize intelligent analyzer if enabled
        if self.use_intelligent_mode:
            if not llm_api_key and not custom_llm_api_key:
                raise ValueError("llm_api_key or custom_llm_api_key required when use_intelligent_mode=True")
            self.analyzer = IntelligentContentAnalyzer(
                llm_api_key, 
                analysis_model,
                custom_llm_base_url,
                custom_llm_api_key
            )
        else:
            self.analyzer = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in the given text."""
        return len(self.encoding.encode(text))
    
    def analyze_content_length(self, content: str) -> Dict[str, any]:
        """
        Analyze content to determine its length characteristics.
        
        Returns:
            Dict with analysis results including token count, word count, etc.
        """
        token_count = self.count_tokens(content)
        word_count = len(content.split())
        char_count = len(content)
        
        # Estimate structure complexity
        paragraph_count = content.count('\n\n') + 1
        has_sections = '##' in content or '###' in content
        
        return {
            'token_count': token_count,
            'word_count': word_count,
            'char_count': char_count,
            'paragraph_count': paragraph_count,
            'has_sections': has_sections,
            'avg_paragraph_tokens': token_count / paragraph_count if paragraph_count > 0 else 0
        }
    
    def determine_processing_mode(self, content: str, force_mode: Optional[ProcessingMode] = None) -> Tuple[ProcessingMode, Dict[str, any]]:
        """
        Determine the best processing mode based on content analysis.
        
        Args:
            content: The content to analyze
            force_mode: Force a specific mode if provided
            
        Returns:
            Tuple of (ProcessingMode, analysis_dict)
        """
        if force_mode:
            analysis = self.analyze_content_length(content)
            return force_mode, analysis
        
        analysis = self.analyze_content_length(content)
        
        # Decision logic based on configured threshold type
        if self.use_word_threshold:
            # Use word count for decision
            threshold_value = analysis['word_count']
            threshold_limit = self.word_threshold
            threshold_type = "words"
        else:
            # Use token count for decision
            threshold_value = analysis['token_count']
            threshold_limit = self.token_threshold
            threshold_type = "tokens"
        
        if threshold_value > threshold_limit:
            # Long content - use paragraph mode
            mode = ProcessingMode.PARAGRAPH
            reason = f"Content has {threshold_value} {threshold_type} (> {threshold_limit} {threshold_type} threshold)"
        else:
            # Short content - use full doc mode
            mode = ProcessingMode.FULL_DOC
            reason = f"Content has {threshold_value} {threshold_type} (≤ {threshold_limit} {threshold_type} threshold)"
        
        # Add detailed analysis to help with debugging
        analysis['selected_mode'] = mode.value
        analysis['selection_reason'] = reason
        analysis['threshold_type'] = threshold_type
        analysis['threshold_value'] = threshold_value
        analysis['threshold_limit'] = threshold_limit
        analysis['decision'] = f"{threshold_value} {threshold_type} {'>' if threshold_value > threshold_limit else '≤'} {threshold_limit}"
        
        return mode, analysis
    
    async def determine_processing_mode_intelligent(self, content: str, url: str) -> Tuple[ProcessingMode, Dict[str, any]]:
        """
        Determine processing mode using intelligent LLM analysis.
        
        Args:
            content: The content to analyze
            url: The URL of the content
            
        Returns:
            Tuple of (ProcessingMode, analysis_dict)
        """
        if not self.analyzer:
            raise ValueError("Intelligent mode not initialized")
        
        # Get LLM analysis
        print(f"  🤖 Running intelligent content analysis...")
        llm_analysis = await self.analyzer.analyze_content(url, content)
        
        # Check if we should skip this page
        should_skip, skip_reason = self.analyzer.should_skip_page(llm_analysis)
        if should_skip:
            print(f"  ⏭️  Skipping page: {skip_reason}")
            llm_analysis['skip'] = True
            llm_analysis['skip_reason'] = skip_reason
            # Return paragraph mode as default, but with skip flag
            return ProcessingMode.PARAGRAPH, llm_analysis
        
        # Determine mode based on analysis
        mode_str, mode_reason = self.analyzer.determine_processing_mode(llm_analysis)
        
        # Convert string to enum
        if mode_str == "full_doc":
            mode = ProcessingMode.FULL_DOC
        else:
            mode = ProcessingMode.PARAGRAPH
        
        # Add basic content metrics
        basic_analysis = self.analyze_content_length(content)
        
        # Combine analyses
        analysis = {
            **basic_analysis,
            **llm_analysis,
            'selected_mode': mode.value,
            'selection_reason': mode_reason,
            'intelligent_analysis': True
        }
        
        return mode, analysis
    
    def get_extraction_prompt(self, mode: ProcessingMode) -> str:
        """
        Get the appropriate extraction prompt based on the processing mode.
        """
        if mode == ProcessingMode.PARAGRAPH:
            return self._get_paragraph_prompt()
        else:
            return self._get_full_doc_prompt()
    
    def _get_paragraph_prompt(self) -> str:
        """Get the paragraph (parent-child) mode prompt."""
        return """You are a RAG Professor creating parent-child hierarchical chunks for a knowledge base.

Your task is to extract and structure content with:
- PARENT sections (marked with ###PARENT_SECTION###) that provide high-level overviews
- CHILD sections (marked with ###CHILD_SECTION###) that contain detailed information

IMPORTANT RULES:
1. Each PARENT should have 2-5 CHILD sections
2. PARENT sections: 500-1500 words (overview, context, summary)
3. CHILD sections: 200-800 words (specific details, examples, procedures)
4. Maintain logical hierarchy - children should relate to their parent
5. Include all important information from the source

Structure your response as:
###PARENT_SECTION###
[Parent content providing overview]

###CHILD_SECTION###
[Detailed child content 1]

###CHILD_SECTION###
[Detailed child content 2]

###PARENT_SECTION###
[Next parent section]

Output ONE JSON object with:
{
  "title": "Document title",
  "name": "Short identifier",
  "description": "The structured content with parent/child sections"
}"""
    
    def _get_full_doc_prompt(self) -> str:
        """Get the full document mode prompt."""
        return """You are a RAG content extractor optimized for shorter documents that benefit from sectioned organization.

This content is SHORT enough to be stored without complex hierarchical chunking. Your task is to:

1. Extract the ENTIRE content without summarization
2. Organize content into logical sections using ###SECTION### markers
3. Preserve ALL details, examples, code snippets, and explanations
4. Create 2-5 sections based on the natural structure of the content

SECTION GUIDELINES:
- Use ###SECTION### to separate major topics or logical divisions
- Each section should be self-contained but connected to the whole
- Section breaks should follow the document's natural structure
- Include section headings as the first line after ###SECTION###

EXAMPLE STRUCTURE:
###SECTION###
## Introduction
[Introduction content...]

###SECTION###
## Getting Started
[Getting started content...]

###SECTION###
## API Reference
[API reference content...]

Output ONE JSON object with:
{
  "title": "Clear, descriptive title of the document",
  "name": "Short identifier",
  "description": "The COMPLETE document content organized with ###SECTION### markers"
}

Remember: This is for SHORTER documents. Use 2-5 sections maximum. Include ALL content."""
    
    def get_dify_configuration(self, mode: ProcessingMode) -> Dict[str, any]:
        """
        Get the Dify API configuration based on the processing mode.
        """
        if mode == ProcessingMode.PARAGRAPH:
            return {
                "doc_form": "hierarchical_model",
                "process_rule": {
                    "mode": "hierarchical",
                    "rules": {
                        "pre_processing_rules": [
                            {"id": "remove_extra_spaces", "enabled": False}, 
                            {"id": "remove_urls_emails", "enabled": False}
                        ],
                        "parent_mode": "paragraph",
                        "segmentation": {
                            "separator": "###PARENT_SECTION###",
                            "max_tokens": self.paragraph_parent_tokens,
                            "chunk_overlap": 100
                        },
                        "subchunk_segmentation": {
                            "separator": "###CHILD_SECTION###",
                            "max_tokens": self.paragraph_child_tokens,
                            "chunk_overlap": 50
                        }
                    }
                }
            }
        else:  # FULL_DOC mode
            return {
                "doc_form": "hierarchical_model",
                "process_rule": {
                    "mode": "hierarchical",
                    "rules": {
                        "pre_processing_rules": [
                            {"id": "remove_extra_spaces", "enabled": False}, 
                            {"id": "remove_urls_emails", "enabled": False}
                        ],
                        "parent_mode": "full-doc",
                        "segmentation": {
                            "separator": "###SECTION###",
                            "max_tokens": self.full_doc_chunk_tokens,
                            "chunk_overlap": 100
                        },
                        "subchunk_segmentation": {
                            "separator": "###SECTION###",
                            "max_tokens": self.full_doc_chunk_tokens,
                            "chunk_overlap": 50
                        }
                    }
                }
            }
    
    def prepare_content_for_mode(self, content: str, mode: ProcessingMode) -> str:
        """
        Prepare content based on the selected mode.
        This can include preprocessing or format adjustments.
        """
        if mode == ProcessingMode.FULL_DOC:
            # For full doc mode, ensure content is clean but complete
            # Remove excessive blank lines but preserve structure
            lines = content.split('\n')
            cleaned_lines = []
            blank_count = 0
            
            for line in lines:
                if line.strip() == '':
                    blank_count += 1
                    if blank_count <= 2:  # Allow up to 2 consecutive blank lines
                        cleaned_lines.append(line)
                else:
                    blank_count = 0
                    cleaned_lines.append(line)
            
            return '\n'.join(cleaned_lines)
        else:
            # For paragraph mode, content is processed by the extraction prompt
            return content
    
    def should_use_full_doc_for_url(self, url: str) -> bool:
        """
        Check if a URL pattern suggests using full doc mode.
        Some content types are better suited for full document storage.
        """
        full_doc_patterns = [
            '/api/',          # API documentation
            '/reference/',    # Reference documentation
            '/glossary',      # Glossaries
            '/faq',          # FAQs
            '/changelog',     # Changelogs
            '/release-notes', # Release notes
            '/examples/',     # Code examples
            '/quickstart',    # Quick start guides
            '/cheatsheet',    # Cheat sheets
        ]
        
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in full_doc_patterns)