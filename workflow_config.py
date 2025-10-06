"""Configuration classes and constants for the crawl workflow."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class SectionMarker(str, Enum):
    """Content section markers used in extraction."""
    PARENT_SECTION = "###PARENT_SECTION###"
    CHILD_SECTION = "###CHILD_SECTION###"
    SECTION = "###SECTION###"
    SECTION_BREAK = "###SECTION_BREAK###"


class ProcessingMode(str, Enum):
    """Document processing modes."""
    FULL_DOC = "full_doc"
    PARAGRAPH = "paragraph"


@dataclass
class WorkflowConfig:
    """Configuration for the crawl workflow.

    This replaces the 14-parameter __init__ with a clean configuration object.
    """
    # API Configuration
    dify_base_url: str = "http://localhost:8088"
    dify_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    custom_llm_base_url: Optional[str] = None
    custom_llm_api_key: Optional[str] = None

    # Model Configuration
    naming_model: str = "gemini/gemini-1.5-flash"
    extraction_model: str = "gemini/gemini-2.0-flash-exp"
    intelligent_analysis_model: str = "gemini/gemini-1.5-flash"

    # Knowledge Base Configuration
    knowledge_base_mode: str = 'automatic'  # 'automatic' or 'manual'
    selected_knowledge_base: Optional[str] = None

    # Processing Configuration
    enable_dual_mode: bool = True
    use_parent_child: bool = True  # Deprecated, kept for backward compatibility
    manual_mode: Optional[str] = None  # 'full_doc' or 'paragraph'

    # Threshold Configuration
    word_threshold: int = 4000
    token_threshold: int = 8000
    use_word_threshold: bool = True

    # Intelligent Mode Configuration
    use_intelligent_mode: bool = False

    # Output Configuration
    output_dir: str = "output"
    prompts_dir: str = "prompts"

    @classmethod
    def from_env(cls, **kwargs):
        """Create configuration from environment variables with overrides."""
        import os
        from dotenv import load_dotenv

        load_dotenv(override=True)

        config = cls(
            dify_base_url=os.getenv('DIFY_BASE_URL', cls.dify_base_url),
            dify_api_key=os.getenv('DIFY_API_KEY'),
            gemini_api_key=os.getenv('GEMINI_API_KEY'),
            **kwargs
        )
        return config

    def validate(self) -> None:
        """Validate configuration."""
        if not self.dify_api_key:
            raise ValueError("DIFY_API_KEY is required")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required")
        if self.knowledge_base_mode not in ['automatic', 'manual']:
            raise ValueError("knowledge_base_mode must be 'automatic' or 'manual'")
        if self.knowledge_base_mode == 'manual' and not self.selected_knowledge_base:
            raise ValueError("selected_knowledge_base is required when using manual mode")
        if self.word_threshold <= 0:
            raise ValueError("word_threshold must be positive")
        if self.token_threshold <= 0:
            raise ValueError("token_threshold must be positive")


@dataclass
class CrawlConfig:
    """Configuration for a single crawl operation."""
    url: str
    max_pages: int = 10
    max_depth: int = 1
    extraction_model: Optional[str] = None  # Override workflow extraction model

    def validate(self) -> None:
        """Validate crawl configuration."""
        if not self.url:
            raise ValueError("URL is required")
        if self.max_pages <= 0:
            raise ValueError("max_pages must be positive")
        if self.max_depth < 0:
            raise ValueError("max_depth must be non-negative")
