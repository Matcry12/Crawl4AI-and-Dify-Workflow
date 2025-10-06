"""Knowledge Base management with single responsibility."""

import logging
from typing import Dict, Optional
from workflow_utils import parse_kb_response, extract_kb_info

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """Manages knowledge base operations with caching."""

    def __init__(self, dify_api):
        """Initialize knowledge base manager.

        Args:
            dify_api: DifyAPI client instance
        """
        self.dify_api = dify_api
        self.knowledge_bases: Dict[str, str] = {}  # name -> id mapping
        self._initialized = False

    async def initialize(self) -> None:
        """Load existing knowledge bases from API."""
        try:
            response = self.dify_api.get_knowledge_base_list()
            if response.status_code == 200:
                kb_data = response.json()
                logger.debug(f"Knowledge bases response: {kb_data}")

                kb_list = parse_kb_response(kb_data)

                for kb in kb_list:
                    try:
                        kb_name, kb_id = extract_kb_info(kb)

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

    async def refresh_cache(self) -> None:
        """Force refresh of knowledge bases cache from API."""
        logger.info("🔄 Refreshing cache from API...")
        self.knowledge_bases.clear()
        await self.initialize()

    async def ensure_exists(self, category: str) -> Optional[str]:
        """Ensure knowledge base exists, create if needed.

        Args:
            category: Category/name for the knowledge base

        Returns:
            Knowledge base ID or None if failed
        """
        # Check cache first
        if category in self.knowledge_bases:
            return self.knowledge_bases[category]

        # Convert category to display name
        kb_name = category.replace('_', ' ').title()

        # Check API for existing KB
        try:
            response = self.dify_api.get_knowledge_base_list()
            if response.status_code == 200:
                kb_data = response.json()
                kb_list = parse_kb_response(kb_data)

                for kb in kb_list:
                    existing_name, kb_id = extract_kb_info(kb)

                    if existing_name and kb_id:
                        if existing_name == kb_name or existing_name.lower().replace(' ', '_') == category:
                            self.knowledge_bases[category] = kb_id
                            logger.info(f"✅ Found existing knowledge base: {existing_name} (ID: {kb_id})")
                            return kb_id
        except Exception as e:
            logger.warning(f"Could not refresh knowledge base list: {e}")

        # Create new knowledge base
        response = self.dify_api.create_empty_knowledge_base(kb_name)

        if response.status_code == 200:
            kb_data = response.json()
            logger.debug(f"Create KB response: {kb_data}")

            kb_id = None
            if isinstance(kb_data, dict):
                kb_id = kb_data.get('id') or kb_data.get('dataset_id') or kb_data.get('uuid')

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

    def get_id(self, name: str) -> Optional[str]:
        """Get knowledge base ID by name.

        Args:
            name: Knowledge base name

        Returns:
            Knowledge base ID or None
        """
        return self.knowledge_bases.get(name)

    def get_all(self) -> Dict[str, str]:
        """Get all cached knowledge bases.

        Returns:
            Dictionary mapping names to IDs
        """
        return self.knowledge_bases.copy()

    def count(self) -> int:
        """Get count of cached knowledge bases.

        Returns:
            Number of knowledge bases
        """
        return len(self.knowledge_bases)
