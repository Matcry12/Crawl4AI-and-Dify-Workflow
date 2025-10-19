"""
Document Merger - Dual Mode Strategy

Intelligently merges topics into documents and creates BOTH formatting modes.

Dual-Mode Strategy:
- Topics ≤4K tokens: Can be merged with similar topics
- Topics >4K tokens: Kept as standalone documents
- ALWAYS creates BOTH modes (full_doc + paragraph) for each document
- RAG system has maximum flexibility to choose best format per query
- Cost: Minimal with Gemini embeddings ($0.000025/1K tokens)
"""

import logging
from typing import Dict, List, Optional
from collections import defaultdict

from core.natural_formatter import NaturalFormatter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentMerger:
    """
    Merge topics into documents with smart strategy.

    Features:
    - Groups topics by category
    - Checks token limits before merging
    - Creates optimized documents for RAG retrieval
    - Uses natural delimiters (## and .)
    """

    def __init__(self, formatter: Optional[NaturalFormatter] = None):
        """
        Initialize the DocumentMerger.

        Args:
            formatter: NaturalFormatter instance (creates new one if not provided)
        """
        self.formatter = formatter or NaturalFormatter()
        logger.info("Initialized DocumentMerger")

    def merge_topics(self, topics: List[Dict]) -> List[Dict]:
        """
        Merge topics into documents based on smart strategy.

        Args:
            topics: List of topic dicts with keys:
                - title: str
                - summary: str
                - category: str
                - content: str

        Returns:
            List of document dicts with keys:
                - title: str
                - category: str
                - content: str (formatted markdown)
                - source_topics: List[str] (titles of merged topics)
                - stats: Dict (token count, section count, mode, strategy)
        """
        logger.info(f"Merging {len(topics)} topics...")

        # Group topics by category
        topics_by_category = self._group_by_category(topics)

        documents = []
        for category, category_topics in topics_by_category.items():
            logger.info(f"Processing category '{category}' with {len(category_topics)} topics")

            # Separate mergeable and standalone topics
            mergeable = []
            standalone = []

            for topic in category_topics:
                if self.formatter.can_merge_topic(topic):
                    mergeable.append(topic)
                else:
                    standalone.append(topic)

            logger.info(f"  Mergeable: {len(mergeable)}, Standalone: {len(standalone)}")

            # Create merged document if there are mergeable topics
            if mergeable:
                merged_doc = self._create_merged_document(category, mergeable)
                documents.append(merged_doc)
                logger.info(f"  Created merged document: {merged_doc['title']}")

            # Create standalone documents
            for topic in standalone:
                standalone_doc = self._create_standalone_document(topic)
                documents.append(standalone_doc)
                logger.info(f"  Created standalone document: {standalone_doc['title']}")

        logger.info(f"Created {len(documents)} documents from {len(topics)} topics")
        return documents

    def merge_topics_dual_mode(self, topics: List[Dict]) -> List[Dict]:
        """
        Merge topics and create BOTH formatting modes for each document.

        This is the new recommended approach - creates both full_doc and paragraph
        versions of each document for maximum RAG flexibility.

        Args:
            topics: List of topic dicts with keys:
                - title: str
                - summary: str
                - category: str
                - content: str

        Returns:
            List of document dicts (2x the number of merge groups):
                Each merge group produces TWO documents:
                1. full_doc version (flat structure, no ## sections)
                2. paragraph version (hierarchical with ## sections)

        Example:
            3 topics in 2 categories → 2 merge groups → 4 documents
            (2 full_doc + 2 paragraph)
        """
        logger.info(f"Dual-mode merging {len(topics)} topics...")

        # Group topics by category
        topics_by_category = self._group_by_category(topics)

        documents = []
        for category, category_topics in topics_by_category.items():
            logger.info(f"Processing category '{category}' with {len(category_topics)} topics")

            # Separate mergeable and standalone topics
            mergeable = []
            standalone = []

            for topic in category_topics:
                if self.formatter.can_merge_topic(topic):
                    mergeable.append(topic)
                else:
                    standalone.append(topic)

            logger.info(f"  Mergeable: {len(mergeable)}, Standalone: {len(standalone)}")

            # Create dual-mode merged documents
            if mergeable:
                dual_docs = self._create_merged_document_dual_mode(category, mergeable)
                documents.extend(dual_docs)
                logger.info(f"  Created 2 merged documents (full_doc + paragraph)")

            # Create dual-mode standalone documents
            for topic in standalone:
                dual_docs = self._create_standalone_document_dual_mode(topic)
                documents.extend(dual_docs)
                logger.info(f"  Created 2 standalone documents (full_doc + paragraph)")

        logger.info(f"Created {len(documents)} documents ({len(documents)//2} × 2 modes) from {len(topics)} topics")
        return documents

    def _group_by_category(self, topics: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group topics by category.

        Args:
            topics: List of topics

        Returns:
            Dict mapping category to list of topics
        """
        grouped = defaultdict(list)
        for topic in topics:
            category = topic.get('category', 'uncategorized')
            grouped[category].append(topic)

        logger.info(f"Grouped topics into {len(grouped)} categories")
        return dict(grouped)

    def _create_merged_document(self, category: str, topics: List[Dict]) -> Dict:
        """
        Create a merged document from multiple topics.

        Uses paragraph mode with ## sections for each topic.

        Args:
            category: Category name
            topics: List of topics to merge

        Returns:
            Document dict with formatted content
        """
        logger.info(f"Creating merged document for category '{category}' with {len(topics)} topics")

        # Create document title
        title = f"{category.replace('_', ' ').title()} - Complete Guide"

        # Build content with ## sections for each topic
        sections = []
        source_topics = []

        for topic in topics:
            # Each topic becomes a ## section
            section_title = topic['title']
            section_content = topic['content']

            # Format as section
            section = f"## {section_title}\n{section_content}"
            sections.append(section)
            source_topics.append(topic['title'])

        # Combine into document
        content = f"# {title}\n" + "\n".join(sections)

        # Get document stats
        stats = self.formatter.get_document_stats(content)

        logger.info(f"Merged document stats: {stats['token_count']} tokens, "
                   f"{stats['section_count']} sections, mode: {stats['mode']}")

        return {
            'title': title,
            'category': category,
            'content': content,
            'source_topics': source_topics,
            'stats': stats,
            'type': 'merged'
        }

    def _create_standalone_document(self, topic: Dict) -> Dict:
        """
        Create a standalone document from a single topic.

        Uses formatter's auto mode to select best format.

        Args:
            topic: Topic to convert to document

        Returns:
            Document dict with formatted content
        """
        logger.info(f"Creating standalone document: {topic['title']}")

        # Format with auto mode (will use full_doc or paragraph based on size)
        content = self.formatter.format_topic(topic, mode='auto')

        # Get document stats
        stats = self.formatter.get_document_stats(content)

        logger.info(f"Standalone document stats: {stats['token_count']} tokens, "
                   f"{stats['section_count']} sections, mode: {stats['mode']}")

        return {
            'title': topic['title'],
            'category': topic.get('category', 'uncategorized'),
            'content': content,
            'source_topics': [topic['title']],
            'stats': stats,
            'type': 'standalone'
        }

    def _create_merged_document_dual_mode(self, category: str, topics: List[Dict]) -> List[Dict]:
        """
        Create BOTH mode versions of a merged document.

        Args:
            category: Category name
            topics: List of topics to merge

        Returns:
            List of 2 documents: [full_doc_version, paragraph_version]
        """
        logger.info(f"Creating dual-mode merged document for '{category}' with {len(topics)} topics")

        # Create base title
        title = f"{category.replace('_', ' ').title()} - Complete Guide"
        source_topics = [topic['title'] for topic in topics]

        # Build content for both modes
        # Paragraph mode: Each topic is a ## section
        paragraph_sections = []
        for topic in topics:
            section = f"## {topic['title']}\n{topic['content']}"
            paragraph_sections.append(section)
        paragraph_content = f"# {title}\n" + "\n".join(paragraph_sections)

        # Full-doc mode: All content in one flat structure (no ## sections)
        full_doc_parts = []
        for topic in topics:
            # Just concatenate content, no section markers
            full_doc_parts.append(topic['content'])
        full_doc_content = f"# {title}\n" + " ".join(full_doc_parts)

        # Get stats for both
        full_doc_stats = self.formatter.get_document_stats(full_doc_content)
        paragraph_stats = self.formatter.get_document_stats(paragraph_content)

        # Force the correct mode in stats
        full_doc_stats['mode'] = 'full_doc'
        paragraph_stats['mode'] = 'paragraph'

        logger.info(f"  Full-doc: {full_doc_stats['token_count']} tokens")
        logger.info(f"  Paragraph: {paragraph_stats['token_count']} tokens, {paragraph_stats['section_count']} sections")

        return [
            {
                'title': title,
                'category': category,
                'content': full_doc_content,
                'source_topics': source_topics,
                'stats': full_doc_stats,
                'type': 'merged',
                'mode': 'full_doc'
            },
            {
                'title': title,
                'category': category,
                'content': paragraph_content,
                'source_topics': source_topics,
                'stats': paragraph_stats,
                'type': 'merged',
                'mode': 'paragraph'
            }
        ]

    def _create_standalone_document_dual_mode(self, topic: Dict) -> List[Dict]:
        """
        Create BOTH mode versions of a standalone document.

        Args:
            topic: Topic to convert to documents

        Returns:
            List of 2 documents: [full_doc_version, paragraph_version]
        """
        logger.info(f"Creating dual-mode standalone document: {topic['title']}")

        # Use the formatter's dual-mode method
        full_doc_content, paragraph_content = self.formatter.format_topic_dual_mode(topic)

        # Get stats for both
        full_doc_stats = self.formatter.get_document_stats(full_doc_content)
        paragraph_stats = self.formatter.get_document_stats(paragraph_content)

        # Force the correct mode in stats
        full_doc_stats['mode'] = 'full_doc'
        paragraph_stats['mode'] = 'paragraph'

        logger.info(f"  Full-doc: {full_doc_stats['token_count']} tokens")
        logger.info(f"  Paragraph: {paragraph_stats['token_count']} tokens, {paragraph_stats['section_count']} sections")

        return [
            {
                'title': topic['title'],
                'category': topic.get('category', 'uncategorized'),
                'content': full_doc_content,
                'source_topics': [topic['title']],
                'stats': full_doc_stats,
                'type': 'standalone',
                'mode': 'full_doc'
            },
            {
                'title': topic['title'],
                'category': topic.get('category', 'uncategorized'),
                'content': paragraph_content,
                'source_topics': [topic['title']],
                'stats': paragraph_stats,
                'type': 'standalone',
                'mode': 'paragraph'
            }
        ]

    def get_merge_statistics(self, documents: List[Dict]) -> Dict:
        """
        Get statistics about merged documents.

        Args:
            documents: List of documents from merge_topics()

        Returns:
            Dict with statistics
        """
        stats = {
            'total_documents': len(documents),
            'merged_documents': sum(1 for d in documents if d['type'] == 'merged'),
            'standalone_documents': sum(1 for d in documents if d['type'] == 'standalone'),
            'total_tokens': sum(d['stats']['token_count'] for d in documents),
            'avg_tokens_per_document': 0,
            'mode_distribution': defaultdict(int)
        }

        if documents:
            stats['avg_tokens_per_document'] = stats['total_tokens'] / len(documents)

        for doc in documents:
            stats['mode_distribution'][doc['stats']['mode']] += 1

        return dict(stats)


if __name__ == "__main__":
    # Quick test
    print("DocumentMerger Test")
    print("=" * 80)

    merger = DocumentMerger()

    # Create test topics
    test_topics = [
        {
            'title': 'Password Security',
            'summary': 'Password best practices',
            'category': 'security',
            'content': '''Strong passwords should be at least 12 characters long.
            Use a mix of uppercase, lowercase, numbers and symbols. Never reuse
            passwords across multiple accounts. Consider using a password manager
            like 1Password or Bitwarden.'''
        },
        {
            'title': 'Two-Factor Authentication',
            'summary': '2FA guide',
            'category': 'security',
            'content': '''Enable 2FA on all accounts. Use authenticator apps instead
            of SMS when possible. Save backup codes in a secure location. Never
            share 2FA codes with anyone.'''
        },
        {
            'title': 'Wallet Backup',
            'summary': 'How to backup wallets',
            'category': 'wallet',
            'content': '''Always backup your wallet seed phrase. Store backups in
            multiple secure locations. Never store seed phrases digitally. Use
            metal backup solutions for fire resistance.'''
        }
    ]

    # Merge topics
    documents = merger.merge_topics(test_topics)

    print(f"\n📊 Created {len(documents)} documents:")
    for i, doc in enumerate(documents, 1):
        print(f"\n{i}. {doc['title']}")
        print(f"   Type: {doc['type']}")
        print(f"   Category: {doc['category']}")
        print(f"   Source topics: {', '.join(doc['source_topics'])}")
        print(f"   Tokens: {doc['stats']['token_count']}")
        print(f"   Sections: {doc['stats']['section_count']}")
        print(f"   Mode: {doc['stats']['mode']}")
        print(f"\n   Content preview:")
        print(f"   {doc['content'][:200]}...")

    # Get statistics
    stats = merger.get_merge_statistics(documents)
    print(f"\n📈 Merge Statistics:")
    print(f"   Total documents: {stats['total_documents']}")
    print(f"   Merged: {stats['merged_documents']}")
    print(f"   Standalone: {stats['standalone_documents']}")
    print(f"   Total tokens: {stats['total_tokens']}")
    print(f"   Avg tokens/doc: {stats['avg_tokens_per_document']:.0f}")
    print(f"\n   Mode distribution:")
    for mode, count in stats['mode_distribution'].items():
        print(f"     {mode}: {count}")

    print("\n" + "=" * 80)
    print("✅ DocumentMerger test complete!")
