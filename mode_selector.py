"""Processing mode selection with simplified logic.

This addresses Issue #11 (Deep Nesting) by using early returns
and extracting complex conditionals into clearer methods.
"""

import logging
from typing import Tuple, Dict, Optional
from workflow_config import ProcessingMode

logger = logging.getLogger(__name__)


class ModeSelector:
    """Selects processing mode with clean, readable logic."""

    def __init__(self, content_processor):
        """Initialize mode selector.

        Args:
            content_processor: ContentProcessor instance
        """
        self.content_processor = content_processor

    async def select_mode(
        self,
        markdown: str,
        url: str,
        manual_mode: Optional[str] = None,
        use_intelligent: bool = False
    ) -> Tuple[Optional[ProcessingMode], Dict]:
        """Select processing mode using early returns for clarity.

        Args:
            markdown: Content to analyze
            url: Source URL
            manual_mode: Manual override ('full_doc' or 'paragraph')
            use_intelligent: Use intelligent LLM-based analysis

        Returns:
            Tuple of (processing_mode, analysis_dict)
        """
        # Early return: Manual mode override
        if manual_mode:
            return self._handle_manual_mode(manual_mode)

        # Early return: Intelligent mode
        if use_intelligent:
            return await self._handle_intelligent_mode(markdown, url)

        # Default: Threshold-based mode
        return self._handle_threshold_mode(markdown, url)

    def _handle_manual_mode(self, manual_mode: str) -> Tuple[ProcessingMode, Dict]:
        """Handle manual mode selection.

        Args:
            manual_mode: 'full_doc' or 'paragraph'

        Returns:
            Tuple of (mode, analysis)
        """
        mode = (
            ProcessingMode.FULL_DOC
            if manual_mode == 'full_doc'
            else ProcessingMode.PARAGRAPH
        )

        logger.info(f"  ✋ Manual mode: {mode.value}")

        return mode, {
            'manual_mode': True,
            'selection_reason': f'Manual override: {manual_mode}'
        }

    async def _handle_intelligent_mode(
        self,
        markdown: str,
        url: str
    ) -> Tuple[Optional[ProcessingMode], Dict]:
        """Handle intelligent LLM-based mode selection.

        Args:
            markdown: Content to analyze
            url: Source URL

        Returns:
            Tuple of (mode, analysis) or (None, analysis) if should skip
        """
        try:
            logger.info(f"  🤖 Running intelligent content analysis...")

            mode, analysis = await self.content_processor.determine_processing_mode_intelligent(
                markdown, url
            )

            # Early return: Skip low-value content
            if analysis.get('skip', False):
                logger.info(f"  ⏭️  Skipping: {analysis.get('skip_reason', 'Low value')}")
                return None, analysis

            # Log analysis results
            self._log_intelligent_results(mode, analysis)

            return mode, analysis

        except Exception as e:
            # Fallback to threshold mode on error
            logger.warning(f"  ⚠️  Intelligent analysis failed: {e}")
            logger.info(f"  🔄 Falling back to threshold-based selection...")
            return self._handle_threshold_mode(markdown, url)

    def _handle_threshold_mode(
        self,
        markdown: str,
        url: str
    ) -> Tuple[ProcessingMode, Dict]:
        """Handle threshold-based mode selection.

        Args:
            markdown: Content to analyze
            url: Source URL

        Returns:
            Tuple of (mode, analysis)
        """
        # Check URL patterns first
        if self._url_suggests_full_doc(url):
            return self._create_url_based_result(url)

        # Use content-based analysis
        mode, analysis = self.content_processor.determine_processing_mode(markdown)

        self._log_threshold_results(mode, analysis)

        return mode, analysis

    def _url_suggests_full_doc(self, url: str) -> bool:
        """Check if URL pattern suggests full doc mode.

        Args:
            url: URL to check

        Returns:
            True if URL suggests full doc mode
        """
        return self.content_processor.should_use_full_doc_for_url(url)

    def _create_url_based_result(self, url: str) -> Tuple[ProcessingMode, Dict]:
        """Create result for URL-based decision.

        Args:
            url: Source URL

        Returns:
            Tuple of (mode, analysis)
        """
        logger.info(f"  📄 URL pattern suggests full doc mode")

        return ProcessingMode.FULL_DOC, {
            'selection_reason': 'URL pattern suggests single-page content',
            'url': url
        }

    def _log_intelligent_results(self, mode: ProcessingMode, analysis: Dict) -> None:
        """Log intelligent analysis results.

        Args:
            mode: Selected processing mode
            analysis: Analysis dictionary
        """
        logger.info(f"  📊 Intelligent analysis results:")
        logger.info(f"     🎯 Content value: {analysis.get('content_value', 'unknown')}")
        logger.info(f"     📋 Structure: {analysis.get('content_structure', 'unknown')}")
        logger.info(f"     📝 Type: {analysis.get('content_type', 'unknown')}")
        logger.info(f"     🔍 Main topics: {', '.join(analysis.get('main_topics', []))}")
        logger.info(f"  📄 Selected mode: {mode.value}")

        reason = analysis.get('mode_reason') or analysis.get('selection_reason', '')
        if reason:
            logger.info(f"     ℹ️  {reason}")

    def _log_threshold_results(self, mode: ProcessingMode, analysis: Dict) -> None:
        """Log threshold-based analysis results.

        Args:
            mode: Selected processing mode
            analysis: Analysis dictionary
        """
        logger.info(f"  📊 Content analysis:")
        logger.info(f"     📝 Word count: {analysis.get('word_count', 0):,} words")
        logger.info(f"     🎯 Token count: {analysis.get('token_count', 0):,} tokens")
        logger.info(f"     📏 Using {analysis.get('threshold_type', 'word')} threshold")
        logger.info(f"     🔍 Decision: {analysis.get('decision', '')}")
        logger.info(f"  📄 Selected mode: {mode.value}")
        logger.info(f"     ℹ️  {analysis.get('selection_reason', '')}")
