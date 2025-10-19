"""
Natural Delimiter Formatter - Dual Mode Strategy

Formats extracted topics using ONLY natural delimiters (standard markdown).
NO custom markers like ###PARENT_SECTION### - uses ##, . only.

Dual-Mode Strategy:
- ALWAYS generates BOTH modes for maximum flexibility
- full_doc: Flat structure with no ## sections (whole document retrieval)
- paragraph: Hierarchical structure with ## sections (section-level retrieval)
- RAG system decides which mode to use for each query

Compatible with Dify chunking and standard markdown parsers.
"""

import os
import logging
from typing import Dict, Optional, List
import litellm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import tiktoken for token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available, using word-based estimation")


class NaturalFormatter:
    """
    Format topics using natural delimiters (standard markdown only).

    Formats topics into clean markdown using:
    - \\n\\n (double newline) for parent section boundaries
    - ## (markdown headings) for section markers
    - . (periods) for sentence boundaries
    - \\n (single newline) for paragraph breaks

    NEVER uses custom markers like ###PARENT_SECTION### or **TITLE:**
    """

    def __init__(self, llm_model: str = "gemini/gemini-2.5-flash-lite", api_key: Optional[str] = None):
        """
        Initialize the NaturalFormatter.

        Args:
            llm_model: LLM model to use for intelligent formatting
            api_key: API key for LLM (defaults to GEMINI_API_KEY env var)
        """
        self.llm_model = llm_model
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')

        # Token thresholds for smart strategy
        self.SMALL_DOC_THRESHOLD = 8000    # ≤8K tokens: full-doc mode
        self.MEDIUM_DOC_THRESHOLD = 16000  # 8K-16K tokens: paragraph with multiple sections
        self.MAX_TOKENS_PER_SECTION = 4000 # Max tokens per ## section

        # Initialize token encoder if available
        if TIKTOKEN_AVAILABLE:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        else:
            self.encoder = None

        logger.info(f"Initialized NaturalFormatter with model: {llm_model}")
        logger.info(f"Token thresholds: Small≤{self.SMALL_DOC_THRESHOLD}, Medium≤{self.MEDIUM_DOC_THRESHOLD}")

    def format_topic(self, topic: Dict, mode: str = "auto") -> str:
        """
        Format topic with natural delimiters (standard markdown).

        Args:
            topic: Dict containing:
                - title: str
                - summary: str
                - category: str
                - content: str
            mode: Formatting mode:
                - "auto": Auto-detect based on content length
                - "paragraph": Multiple sections (for longer content)
                - "full_doc": Simpler structure (for shorter content)

        Returns:
            Formatted markdown string using ONLY natural delimiters

        Example:
            >>> formatter = NaturalFormatter()
            >>> topic = {
            ...     'title': 'Test Topic',
            ...     'summary': 'Summary',
            ...     'category': 'test',
            ...     'content': 'Content here.'
            ... }
            >>> formatted = formatter.format_topic(topic, mode='auto')
            >>> '###PARENT_SECTION###' not in formatted  # Never has custom markers
            True
        """
        logger.info(f"Formatting topic: {topic.get('title', 'Unknown')} (mode: {mode})")

        # Detect mode if auto
        if mode == "auto":
            detected_mode = self.detect_mode(topic['content'])
            logger.info(f"Auto-detected mode: {detected_mode}")
            mode = detected_mode

        # Format based on mode
        if mode == "paragraph":
            formatted = self._format_paragraph_mode(topic)
        else:  # full_doc
            formatted = self._format_full_doc_mode(topic)

        # Clean up formatting (remove excessive newlines)
        formatted = self._clean_formatting(formatted)

        # Validate output (ensure no custom markers)
        if not self._validate_output(formatted):
            logger.warning("Validation failed! Using fallback formatting")
            formatted = self._simple_fallback_format(topic, mode)

        logger.info(f"Formatting complete: {len(formatted)} chars")
        return formatted

    def format_topic_dual_mode(self, topic: Dict) -> tuple[str, str]:
        """
        Format topic in BOTH modes for maximum retrieval flexibility.

        This is the new recommended approach - generate both full_doc and paragraph
        versions so the RAG system can choose the best format for each query.

        Args:
            topic: Dict containing:
                - title: str
                - summary: str
                - category: str
                - content: str

        Returns:
            Tuple of (full_doc_content, paragraph_content)

        Example:
            >>> formatter = NaturalFormatter()
            >>> topic = {'title': 'Test', 'content': 'Content...'}
            >>> full_doc, paragraph = formatter.format_topic_dual_mode(topic)
            >>> '##' not in full_doc  # Full-doc has no sections
            True
            >>> '##' in paragraph  # Paragraph has sections
            True
        """
        logger.info(f"Dual-mode formatting: {topic.get('title', 'Unknown')}")

        # Generate both modes
        full_doc = self._format_full_doc_mode(topic)
        paragraph = self._format_paragraph_mode(topic)

        # Clean both
        full_doc = self._clean_formatting(full_doc)
        paragraph = self._clean_formatting(paragraph)

        # Validate both
        if not self._validate_output(full_doc):
            logger.warning("Full-doc validation failed, using fallback")
            full_doc = self._simple_fallback_format(topic, "full_doc")

        if not self._validate_output(paragraph):
            logger.warning("Paragraph validation failed, using fallback")
            paragraph = self._simple_fallback_format(topic, "paragraph")

        logger.info(f"Dual-mode complete: full_doc={len(full_doc)} chars, paragraph={len(paragraph)} chars")

        return full_doc, paragraph

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if self.encoder:
            return len(self.encoder.encode(text))
        else:
            # Fallback: estimate tokens as words * 1.3
            return int(len(text.split()) * 1.3)

    def detect_mode(self, content: str) -> str:
        """
        Auto-detect best formatting mode based on token count.

        Strategy:
        - ≤8K tokens: full-doc (return entire document in retrieval)
        - >8K tokens: paragraph (return specific sections in retrieval)

        Args:
            content: The topic content to analyze

        Returns:
            "full_doc" or "paragraph"
        """
        token_count = self.count_tokens(content)

        logger.info(f"Content has {token_count} tokens")

        if token_count <= self.SMALL_DOC_THRESHOLD:
            logger.info("Using full-doc mode (≤8K tokens)")
            return "full_doc"
        else:
            logger.info("Using paragraph mode (>8K tokens)")
            return "paragraph"

    def can_merge_topic(self, topic: Dict) -> bool:
        """
        Check if a topic can be merged into a document.

        A topic can be merged only if it's ≤4000 tokens (one section).

        Args:
            topic: Topic to check

        Returns:
            True if topic can be merged, False otherwise
        """
        token_count = self.count_tokens(topic['content'])

        if token_count <= self.MAX_TOKENS_PER_SECTION:
            logger.info(f"Topic '{topic['title']}' can be merged ({token_count} tokens)")
            return True
        else:
            logger.warning(f"Topic '{topic['title']}' is too large to merge ({token_count} tokens > {self.MAX_TOKENS_PER_SECTION})")
            return False

    def get_document_stats(self, content: str) -> Dict:
        """
        Get statistics about a formatted document.

        Args:
            content: Formatted document content

        Returns:
            Dict with token_count, section_count, mode
        """
        token_count = self.count_tokens(content)
        section_count = content.count('##')

        # Determine mode based on token count
        if token_count <= self.SMALL_DOC_THRESHOLD:
            mode = 'full_doc'
        else:
            mode = 'paragraph'

        return {
            'token_count': token_count,
            'section_count': section_count,
            'mode': mode
        }

    def _format_paragraph_mode(self, topic: Dict) -> str:
        """
        Format topic with multiple sections (paragraph mode).

        Uses LLM to intelligently structure content into multiple sections
        with natural markdown formatting.

        Args:
            topic: Topic data dict

        Returns:
            Formatted markdown with multiple ## sections
        """
        logger.info(f"Formatting in paragraph mode: {topic['title']}")

        # Create strict prompt
        prompt = self._create_paragraph_prompt(topic)

        # Call LLM
        try:
            formatted = self._call_llm(prompt)
            return formatted.strip()
        except Exception as e:
            logger.error(f"LLM call failed in paragraph mode: {e}")
            return self._simple_fallback_format(topic, "paragraph")

    def _format_full_doc_mode(self, topic: Dict) -> str:
        """
        Format topic with simpler structure (full-doc mode).

        Uses LLM to create a simpler format with 2-3 sections max.

        Args:
            topic: Topic data dict

        Returns:
            Formatted markdown with simpler structure
        """
        logger.info(f"Formatting in full-doc mode: {topic['title']}")

        # Create strict prompt
        prompt = self._create_full_doc_prompt(topic)

        # Call LLM
        try:
            formatted = self._call_llm(prompt)
            return formatted.strip()
        except Exception as e:
            logger.error(f"LLM call failed in full-doc mode: {e}")
            return self._simple_fallback_format(topic, "full_doc")

    def _create_paragraph_prompt(self, topic: Dict) -> str:
        """Create LLM prompt for paragraph mode formatting."""
        return f"""You are a markdown formatter for hierarchical chunking systems.

CRITICAL DELIMITER RULES:
1. Parent delimiter: ## (markdown heading) - Use ONLY for major section boundaries
2. Child delimiter: . (period) - Use ONLY to separate sentences
3. NO other delimiters - NO \\n\\n, NO extra newlines between sentences
4. Each ## section contains multiple sentences separated by periods and spaces

Structure MUST be:
# {topic['title']}
## Section 1
Sentence one. Sentence two. Sentence three.
## Section 2
Sentence four. Sentence five. Sentence six.

WRONG (do NOT do this):
# Title
## Section 1

Sentence one.
Sentence two.

## Section 2

Sentence three.

CORRECT format:
# Title
## Section 1
Sentence one. Sentence two. Sentence three.
## Section 2
Sentence four. Sentence five.

Topic to format:
Title: {topic['title']}
Content: {topic['content']}

OUTPUT ONLY THE FORMATTED MARKDOWN. Create 3-5 logical sections."""

    def _create_full_doc_prompt(self, topic: Dict) -> str:
        """Create LLM prompt for full-doc mode formatting."""
        return f"""You are a markdown formatter for flat chunking systems.

CRITICAL DELIMITER RULES:
1. Child delimiter ONLY: . (period) - Use ONLY to separate sentences
2. NO parent sections - NO ## headings in the content
3. NO extra delimiters - NO \\n\\n, NO extra newlines
4. Simple flat structure: title + sentences separated by periods and spaces

Structure MUST be:
# {topic['title']}
Sentence one. Sentence two. Sentence three. Sentence four.

WRONG (do NOT do this):
# Title
## Section 1
Content here.

WRONG (do NOT do this):
# Title

Sentence one.

Sentence two.

CORRECT format:
# Title
Sentence one. Sentence two. Sentence three. Sentence four.

Topic to format:
Title: {topic['title']}
Content: {topic['content']}

OUTPUT ONLY THE FORMATTED MARKDOWN. All content after the title in one continuous paragraph."""

    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM to format the topic.

        Args:
            prompt: The formatting prompt

        Returns:
            Formatted markdown string
        """
        try:
            # Try litellm first
            response = litellm.completion(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.api_key,
                temperature=0.3  # Lower temperature for consistent formatting
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"litellm failed: {e}, trying direct API call")
            # Fallback to direct API call
            return self._call_llm_direct(prompt)

    def _call_llm_direct(self, prompt: str) -> str:
        """Fallback: Direct API call to Gemini."""
        import requests

        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.llm_model.replace('gemini/', '')}:generateContent"

        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048
            }
        }

        response = requests.post(
            f"{api_url}?key={self.api_key}",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']

    def _validate_output(self, formatted: str) -> bool:
        """
        Validate that output contains NO custom markers and uses proper delimiters.

        This is CRITICAL - we must never use custom markers.

        Args:
            formatted: The formatted markdown to validate

        Returns:
            True if valid (no custom markers), False otherwise
        """
        forbidden_markers = [
            '###PARENT_SECTION###',
            '###CHILD_SECTION###',
            '###SECTION###',
            '**TITLE:**',
            '**OVERVIEW:**',
            '**CONTENT:**',
            '**SUMMARY:**'
        ]

        for marker in forbidden_markers:
            if marker in formatted:
                logger.error(f"VALIDATION FAILED: Found forbidden marker: {marker}")
                return False

        # Check for excessive newlines (should not have multiple consecutive blank lines)
        if '\n\n\n' in formatted:
            logger.warning("Found excessive newlines, will clean up")
            # Don't fail validation, but this indicates suboptimal formatting

        return True

    def _clean_formatting(self, formatted: str) -> str:
        """
        Clean up the formatted output to ensure proper delimiter usage.

        Removes excessive newlines while preserving structure.

        Args:
            formatted: The formatted markdown

        Returns:
            Cleaned markdown
        """
        # Replace multiple consecutive newlines with single newlines
        import re

        # First, normalize all multiple newlines to single newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', formatted)

        # Ensure proper structure: heading followed by single newline, then content
        # Pattern: ## Heading\n\nContent -> ## Heading\nContent
        cleaned = re.sub(r'(##[^\n]+)\n\n+', r'\1\n', cleaned)

        # Pattern: # Title\n\nContent -> # Title\nContent
        cleaned = re.sub(r'(#[^#][^\n]+)\n\n+', r'\1\n', cleaned)

        return cleaned.strip()

    def _simple_fallback_format(self, topic: Dict, mode: str) -> str:
        """
        Simple fallback formatting (no LLM needed).

        Used when LLM fails or validation fails.

        Args:
            topic: Topic data dict
            mode: Formatting mode

        Returns:
            Basic formatted markdown with proper delimiters
        """
        logger.info(f"Using simple fallback formatting ({mode} mode)")

        # Split content into sentences
        content = topic['content']
        sentences = [s.strip() for s in content.split('.') if s.strip()]

        # Ensure sentences end with periods
        sentences = [s if s.endswith('.') else s + '.' for s in sentences]

        # Create basic structure
        if mode == "paragraph":
            # Paragraph mode: ## for parents, . for children
            formatted = f"# {topic['title']}\n"

            # Split sentences into sections (about 3-4 sentences per section)
            sentences_per_section = 3
            num_sections = max(2, len(sentences) // sentences_per_section)

            section_names = ["Overview", "Key Points", "Details", "Additional Information", "Summary"]

            for i in range(num_sections):
                start_idx = i * sentences_per_section
                end_idx = start_idx + sentences_per_section
                section_sentences = sentences[start_idx:end_idx]

                if section_sentences:
                    section_name = section_names[i] if i < len(section_names) else f"Section {i+1}"
                    formatted += f"## {section_name}\n"
                    formatted += ' '.join(section_sentences) + "\n"

        else:  # full_doc
            # Full-doc mode: only . for children, no ## parents
            formatted = f"# {topic['title']}\n"
            formatted += ' '.join(sentences) + "\n"

        return formatted.strip()


if __name__ == "__main__":
    # Quick test
    print("NaturalFormatter Test")
    print("=" * 80)

    formatter = NaturalFormatter()

    # Test topic
    test_topic = {
        'title': 'Password Security Best Practices',
        'summary': 'Guidelines for creating and managing strong passwords',
        'category': 'wallet_security',
        'content': '''Password security is crucial for cryptocurrency accounts.
        Strong passwords should be at least 12 characters long.
        Use a mix of uppercase, lowercase, numbers and symbols.
        Never reuse passwords across multiple accounts.
        Consider using a password manager like 1Password or Bitwarden.
        Enable two-factor authentication whenever possible.'''
    }

    print(f"\nFormatting: {test_topic['title']}")
    print(f"Content length: {len(test_topic['content'].split())} words")

    # Test auto mode
    formatted = formatter.format_topic(test_topic, mode='auto')

    print("\n" + "=" * 80)
    print("FORMATTED OUTPUT:")
    print("=" * 80)
    print(formatted)
    print("=" * 80)

    # Validate no custom markers
    forbidden = ['###PARENT', '###CHILD', '**TITLE:**']
    has_custom_markers = any(marker in formatted for marker in forbidden)

    print(f"\nValidation:")
    print(f"  Has custom markers: {has_custom_markers} (should be False)")
    print(f"  Has ## headings: {'##' in formatted}")
    print(f"  Has \\n\\n breaks: {formatted.count(chr(10) + chr(10))}")
    print(f"  Has periods: {formatted.count('.')}")

    if not has_custom_markers:
        print("\n✅ SUCCESS: No custom markers found!")
    else:
        print("\n❌ FAILED: Found custom markers!")
