"""Example of refactored workflow using separated components.

This demonstrates the improved architecture with:
- Configuration objects instead of 14 parameters
- Separated responsibilities (KB, Document, Metadata managers)
- Dependency injection
- Cleaner, more maintainable code
"""

import asyncio
import logging
from workflow_config import WorkflowConfig, CrawlConfig
from knowledge_base_manager import KnowledgeBaseManager
from document_manager import DocumentManager
from metadata_manager import MetadataManager
from tests.Test_dify import DifyAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RefactoredCrawlWorkflow:
    """Refactored crawl workflow with separated concerns.

    This is a simplified example showing how the architecture has been improved.
    """

    def __init__(self, config: WorkflowConfig):
        """Initialize with configuration object.

        Args:
            config: WorkflowConfig instance
        """
        config.validate()
        self.config = config

        # Initialize API client (dependency injection)
        self.dify_api = DifyAPI(
            base_url=config.dify_base_url,
            api_key=config.dify_api_key
        )

        # Initialize specialized managers (single responsibility)
        self.kb_manager = KnowledgeBaseManager(self.dify_api)
        self.doc_manager = DocumentManager(self.dify_api)
        self.metadata_manager = MetadataManager(self.dify_api)

    async def initialize(self) -> None:
        """Initialize workflow components."""
        logger.info("🚀 Initializing workflow components...")
        await self.kb_manager.initialize()
        await self.doc_manager.preload_all(self.kb_manager.get_all())
        logger.info("✅ Workflow initialized")

    async def check_duplicate(self, url: str) -> bool:
        """Check if URL already exists.

        Args:
            url: URL to check

        Returns:
            True if duplicate exists
        """
        exists, kb_id, doc_name = await self.doc_manager.check_url_exists(
            url, self.kb_manager.get_all()
        )

        if exists:
            logger.info(f"⏭️  Duplicate: {url} exists as '{doc_name}' in KB {kb_id}")
            return True

        return False

    async def process_document(
        self,
        url: str,
        content: str,
        title: str,
        category: str,
        processing_mode
    ) -> bool:
        """Process and upload a document with metadata.

        Args:
            url: Source URL
            content: Document content
            title: Document title
            category: Knowledge base category
            processing_mode: ProcessingMode enum

        Returns:
            True if successful
        """
        # Ensure KB exists
        kb_id = await self.kb_manager.ensure_exists(category)
        if not kb_id:
            logger.error(f"❌ Failed to get/create KB for category: {category}")
            return False

        # Generate document name
        doc_name = self.doc_manager.generate_document_name(url)

        # Check if already exists
        if self.doc_manager.document_exists(kb_id, doc_name):
            logger.info(f"⏭️  Document already exists: {doc_name}")
            return True

        # Create document
        response = self.dify_api.create_document_from_text(
            dataset_id=kb_id,
            name=doc_name,
            text=content
        )

        if response.status_code != 200:
            logger.error(f"❌ Failed to create document: {response.text}")
            return False

        doc_data = response.json()
        doc_id = doc_data.get('id') or doc_data.get('document', {}).get('id')

        if not doc_id:
            logger.error(f"❌ No document ID returned")
            return False

        # Add to cache
        self.doc_manager.add_document(kb_id, doc_name, doc_id)
        logger.info(f"✅ Created document: {doc_name} (ID: {doc_id})")

        # Ensure metadata fields exist
        metadata_fields = await self.metadata_manager.ensure_metadata_fields(kb_id)

        # Prepare and assign metadata
        word_count = len(content.split())
        metadata_list = self.metadata_manager.prepare_document_metadata(
            url, processing_mode, word_count, metadata_fields
        )

        await self.metadata_manager.assign_metadata(kb_id, doc_id, metadata_list)

        return True


async def main():
    """Example usage of refactored workflow."""

    # Create configuration from environment
    config = WorkflowConfig.from_env(
        enable_dual_mode=True,
        word_threshold=4000,
        use_intelligent_mode=False
    )

    # Initialize workflow
    workflow = RefactoredCrawlWorkflow(config)
    await workflow.initialize()

    # Example: Process a document
    from workflow_config import ProcessingMode

    url = "https://docs.example.com/guide"
    content = "This is example documentation content..."
    title = "Example Guide"
    category = "documentation"

    # Check for duplicates first
    if await workflow.check_duplicate(url):
        logger.info("Document already exists, skipping")
        return

    # Process the document
    success = await workflow.process_document(
        url=url,
        content=content,
        title=title,
        category=category,
        processing_mode=ProcessingMode.FULL_DOC
    )

    if success:
        logger.info("✅ Document processed successfully")
    else:
        logger.error("❌ Document processing failed")

    # Show statistics
    logger.info(f"\n📊 Statistics:")
    logger.info(f"  Knowledge bases: {workflow.kb_manager.count()}")
    logger.info(f"  Documents cached: {workflow.doc_manager.get_total_count()}")


if __name__ == "__main__":
    asyncio.run(main())
