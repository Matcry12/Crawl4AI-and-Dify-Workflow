"""Metadata management for knowledge base documents."""

import logging
from typing import Dict, List
from datetime import datetime
from workflow_config import ProcessingMode
from workflow_utils import get_domain_from_url, detect_content_type_from_url

logger = logging.getLogger(__name__)


class MetadataManager:
    """Manages metadata fields and assignments for documents."""

    # Standard metadata fields for crawled content
    REQUIRED_FIELDS = {
        'source_url': 'string',
        'crawl_date': 'time',
        'domain': 'string',
        'content_type': 'string',
        'processing_mode': 'string',
        'word_count': 'number'
    }

    def __init__(self, dify_api):
        """Initialize metadata manager.

        Args:
            dify_api: DifyAPI client instance
        """
        self.dify_api = dify_api
        self.metadata_cache: Dict[str, Dict[str, Dict]] = {}  # kb_id -> {name: {id, type}}

    async def ensure_metadata_fields(self, kb_id: str) -> Dict[str, Dict]:
        """Ensure standard metadata fields exist in a knowledge base.

        Args:
            kb_id: Knowledge base ID

        Returns:
            Dictionary mapping metadata names to their IDs and types
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

        # Create missing fields
        for field_name, field_type in self.REQUIRED_FIELDS.items():
            if field_name not in existing_metadata:
                logger.info(f"  ➕ Creating metadata field: {field_name} ({field_type})")
                response = self.dify_api.create_knowledge_metadata(kb_id, field_type, field_name)

                logger.debug(f"    Response status: {response.status_code}")
                logger.debug(f"    Response body: {response.text}")

                if response.status_code in [200, 201]:
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

    def prepare_document_metadata(
        self,
        url: str,
        processing_mode: ProcessingMode,
        word_count: int,
        metadata_fields: Dict[str, Dict]
    ) -> List[Dict]:
        """Prepare metadata values for a document.

        Args:
            url: Source URL
            processing_mode: ProcessingMode enum value
            word_count: Word count of content
            metadata_fields: Available metadata fields {name: {id, type}}

        Returns:
            List of metadata assignments [{"id": "...", "value": "...", "name": "..."}]
        """
        domain = get_domain_from_url(url)
        content_type = detect_content_type_from_url(url)
        current_time = int(datetime.now().timestamp())

        metadata_values = {
            'source_url': url,
            'crawl_date': current_time,
            'domain': domain,
            'content_type': content_type,
            'processing_mode': processing_mode.value if processing_mode else 'unknown',
            'word_count': word_count
        }

        metadata_list = []
        for field_name, value in metadata_values.items():
            if field_name in metadata_fields:
                field_info = metadata_fields[field_name]
                metadata_list.append({
                    'id': field_info['id'],
                    'value': value,
                    'name': field_name
                })

        return metadata_list

    async def assign_metadata(
        self,
        kb_id: str,
        doc_id: str,
        metadata_list: List[Dict]
    ) -> bool:
        """Assign metadata to a document.

        Args:
            kb_id: Knowledge base ID
            doc_id: Document ID
            metadata_list: List of metadata assignments

        Returns:
            True if successful
        """
        if not metadata_list:
            return True

        logger.info(f"  🏷️  Assigning {len(metadata_list)} metadata fields...")
        response = self.dify_api.assign_document_metadata(kb_id, doc_id, metadata_list)

        if response.status_code == 200:
            logger.info(f"    ✅ Metadata assigned successfully")
            for meta in metadata_list:
                if meta['name'] in ['source_url', 'domain', 'content_type', 'processing_mode']:
                    logger.info(f"      • {meta['name']}: {meta['value']}")
            return True
        else:
            logger.warning(f"    ⚠️  Failed to assign metadata: {response.text}")
            return False

    def clear_cache(self, kb_id: Optional[str] = None) -> None:
        """Clear metadata cache.

        Args:
            kb_id: Optional specific KB to clear, or None for all
        """
        if kb_id:
            self.metadata_cache.pop(kb_id, None)
        else:
            self.metadata_cache.clear()
