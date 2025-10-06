"""Document management with duplicate detection."""

import logging
from typing import Dict, Tuple, Optional
from urllib.parse import urlparse
from workflow_utils import normalize_url, sanitize_filename

logger = logging.getLogger(__name__)


class DocumentManager:
    """Manages document operations with caching and duplicate detection."""

    def __init__(self, dify_api):
        """Initialize document manager.

        Args:
            dify_api: DifyAPI client instance
        """
        self.dify_api = dify_api
        self.document_cache: Dict[str, Dict[str, str]] = {}  # kb_id -> {doc_name: doc_id}

    def generate_document_name(self, url: str, title: Optional[str] = None) -> str:
        """Generate consistent document name from URL.

        Note: Title is intentionally ignored to ensure consistency between
        checking (before we have title) and pushing (after we have title).

        Args:
            url: Source URL
            title: Document title (ignored for consistency)

        Returns:
            Sanitized document name

        Examples:
            >>> dm = DocumentManager(None)
            >>> dm.generate_document_name("https://example.com/docs/guide")
            'example.com_docs_guide'
        """
        # Normalize URL first
        url = normalize_url(url)

        # Parse URL to get meaningful parts
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        path = parsed.path.strip('/')

        # Create base name from domain and path
        if path:
            path_clean = path.replace('/', '_').replace('-', '_')
            base_name = f"{domain}_{path_clean}"
        else:
            base_name = domain

        # Add query parameters if present
        if parsed.query:
            query_clean = parsed.query[:20].replace('&', '_').replace('=', '_')
            base_name = f"{base_name}_q_{query_clean}"

        # Sanitize and return
        return sanitize_filename(base_name)

    async def load_documents_for_kb(self, kb_id: str) -> Dict[str, str]:
        """Load all documents for a knowledge base into cache.

        Args:
            kb_id: Knowledge base ID

        Returns:
            Dictionary mapping document names to IDs
        """
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

                if not data.get('has_more', False):
                    break

                page += 1

            self.document_cache[kb_id] = documents
            logger.info(f"📚 Loaded {len(documents)} existing documents for knowledge base {kb_id}")

        except Exception as e:
            logger.error(f"❌ Error loading documents for KB {kb_id}: {e}")
            self.document_cache[kb_id] = {}

        return documents

    async def check_url_exists(self, url: str, kb_id_name_map: Dict[str, str]) -> Tuple[bool, Optional[str], str]:
        """Check if a URL already exists in any knowledge base.

        Args:
            url: URL to check
            kb_id_name_map: Dictionary mapping KB names to IDs

        Returns:
            Tuple of (exists, kb_id, doc_name)
        """
        url = normalize_url(url)
        doc_name = self.generate_document_name(url)

        for kb_name, kb_id in kb_id_name_map.items():
            if kb_id not in self.document_cache:
                await self.load_documents_for_kb(kb_id)

            if doc_name in self.document_cache.get(kb_id, {}):
                return True, kb_id, doc_name

        return False, None, doc_name

    async def preload_all(self, kb_id_name_map: Dict[str, str]) -> None:
        """Preload all documents from all knowledge bases.

        Args:
            kb_id_name_map: Dictionary mapping KB names to IDs
        """
        logger.info("📚 Preloading all documents from knowledge bases...")
        total_docs = 0

        for kb_name, kb_id in kb_id_name_map.items():
            docs = await self.load_documents_for_kb(kb_id)
            total_docs += len(docs)

        logger.info(f"✅ Preloaded {total_docs} documents from {len(kb_id_name_map)} knowledge bases")

    def get_document_id(self, kb_id: str, doc_name: str) -> Optional[str]:
        """Get document ID by name.

        Args:
            kb_id: Knowledge base ID
            doc_name: Document name

        Returns:
            Document ID or None
        """
        return self.document_cache.get(kb_id, {}).get(doc_name)

    def add_document(self, kb_id: str, doc_name: str, doc_id: str) -> None:
        """Add document to cache.

        Args:
            kb_id: Knowledge base ID
            doc_name: Document name
            doc_id: Document ID
        """
        if kb_id not in self.document_cache:
            self.document_cache[kb_id] = {}
        self.document_cache[kb_id][doc_name] = doc_id

    def document_exists(self, kb_id: str, doc_name: str) -> bool:
        """Check if document exists in cache.

        Args:
            kb_id: Knowledge base ID
            doc_name: Document name

        Returns:
            True if document exists
        """
        return doc_name in self.document_cache.get(kb_id, {})

    def get_total_count(self) -> int:
        """Get total number of cached documents.

        Returns:
            Total document count
        """
        return sum(len(docs) for docs in self.document_cache.values())
