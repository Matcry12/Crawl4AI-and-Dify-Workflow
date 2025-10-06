"""Utility functions for the crawl workflow."""

import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """Normalize URL by removing trailing slash.

    Args:
        url: URL to normalize

    Returns:
        Normalized URL
    """
    return url.rstrip('/')


def parse_kb_response(kb_data: Any) -> List[Dict[str, Any]]:
    """Parse knowledge base API response into standardized list format.

    Handles different possible response structures from Dify API.

    Args:
        kb_data: Response data from Dify API

    Returns:
        List of knowledge base dictionaries

    Examples:
        >>> parse_kb_response({'data': [{'id': '123', 'name': 'KB1'}]})
        [{'id': '123', 'name': 'KB1'}]
    """
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

    return kb_list if isinstance(kb_list, list) else []


def extract_kb_info(kb: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """Extract knowledge base name and ID from API response.

    Args:
        kb: Knowledge base dictionary from API

    Returns:
        Tuple of (kb_name, kb_id) or (None, None) if invalid

    Examples:
        >>> extract_kb_info({'name': 'Test', 'id': '123'})
        ('Test', '123')
    """
    if not isinstance(kb, dict):
        return None, None

    # Try different possible field names
    kb_name = kb.get('name') or kb.get('title') or kb.get('dataset_name')
    kb_id = kb.get('id') or kb.get('dataset_id') or kb.get('uuid')

    return kb_name, kb_id


def get_domain_from_url(url: str) -> str:
    """Extract domain from URL.

    Args:
        url: Full URL

    Returns:
        Domain without 'www.' prefix

    Examples:
        >>> get_domain_from_url('https://www.example.com/path')
        'example.com'
    """
    parsed = urlparse(url)
    return parsed.netloc.replace('www.', '')


def detect_content_type_from_url(url: str) -> str:
    """Detect content type from URL path.

    Args:
        url: Full URL

    Returns:
        Content type string

    Examples:
        >>> detect_content_type_from_url('https://example.com/docs/guide')
        'documentation'
    """
    path_lower = urlparse(url).path.lower()

    if any(x in path_lower for x in ['/docs/', '/documentation/', '/guide/']):
        return 'documentation'
    elif any(x in path_lower for x in ['/blog/', '/article/', '/news/']):
        return 'article'
    elif any(x in path_lower for x in ['/tutorial/', '/how-to/']):
        return 'tutorial'
    elif any(x in path_lower for x in ['/api/', '/reference/']):
        return 'api_reference'
    else:
        return 'general'


def count_words(text: str) -> int:
    """Count words in text.

    Args:
        text: Text to count words in

    Returns:
        Word count

    Examples:
        >>> count_words("Hello world")
        2
    """
    return len(text.split())


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """Sanitize string for use as filename.

    Args:
        name: String to sanitize
        max_length: Maximum length of result

    Returns:
        Sanitized filename string

    Examples:
        >>> sanitize_filename("Hello/World?")
        'HelloWorld'
    """
    # Remove special characters and limit length
    sanitized = ''.join(c for c in name if c.isalnum() or c in ['_', '-', '.'])
    return sanitized[:max_length]
