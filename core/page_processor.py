"""
Page Processor - Complete Workflow Orchestrator

Orchestrates the complete topic-based RAG pipeline:
1. Extract topics from crawled page content
2. Merge topics into documents
3. Generate embeddings
4. Save to PostgreSQL database

Smart Strategy:
- Topics ≤4K tokens: Can be merged with similar topics
- Topics >4K tokens: Saved as standalone documents
- Documents ≤8K tokens: Use full_doc mode (flat structure)
- Documents >8K tokens: Use paragraph mode (hierarchical with ## sections)
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

# Optional: psycopg2 for PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import execute_values
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logging.warning("psycopg2 not available, database save will not work")

# Optional: numpy for embeddings
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logging.warning("numpy not available, using list for embeddings")

# Optional: sentence-transformers for embeddings (legacy support)
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available")

# Gemini embeddings (preferred, cheaper)
try:
    from core.gemini_embeddings import GeminiEmbeddings
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Gemini embeddings not available")

from core.document_merger import DocumentMerger
from core.natural_formatter import NaturalFormatter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PageProcessor:
    """
    Complete workflow orchestrator for topic-based RAG.

    Features:
    - Extract topics from pages
    - Merge topics into documents
    - Generate embeddings
    - Save to PostgreSQL with pgvector
    """

    def __init__(
        self,
        db_config: Optional[Dict] = None,
        embedding_provider: str = "gemini",
        embedding_model: str = None
    ):
        """
        Initialize the PageProcessor.

        Args:
            db_config: PostgreSQL connection config with keys:
                - host: Database host (default: localhost)
                - port: Database port (default: 5432)
                - database: Database name (default: crawl4ai)
                - user: Database user (default: postgres)
                - password: Database password
            embedding_provider: Embedding provider to use:
                - "gemini" (default): Gemini text-embedding-004 (768D, $0.000025/1K tokens)
                - "sentence-transformers": Local models (384D, free but requires resources)
            embedding_model: Model name (optional, uses defaults if not specified)
        """
        # Initialize components
        self.formatter = NaturalFormatter()
        self.merger = DocumentMerger(formatter=self.formatter)

        # Database configuration
        self.db_config = db_config or {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'crawl4ai'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '')
        }

        # Initialize embedding model based on provider
        self.embedding_provider = embedding_provider
        self.embedding_model = None
        self.embedding_dimension = 0

        if embedding_provider == "gemini":
            if GEMINI_AVAILABLE:
                logger.info("Loading Gemini embeddings (text-embedding-004, 768D)")
                self.embedding_model = GeminiEmbeddings()
                self.embedding_dimension = 768
                logger.info("Gemini embeddings loaded successfully")
            else:
                logger.error("Gemini embeddings not available, please install: pip install google-generativeai")

        elif embedding_provider == "sentence-transformers":
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                model_name = embedding_model or "all-MiniLM-L6-v2"
                logger.info(f"Loading sentence-transformers model: {model_name} (384D)")
                self.embedding_model = SentenceTransformer(model_name)
                self.embedding_dimension = 384
                logger.info(f"Sentence-transformers model loaded: {model_name}")
            else:
                logger.error("sentence-transformers not available, please install: pip install sentence-transformers")

        else:
            logger.error(f"Unknown embedding provider: {embedding_provider}")

        if not self.embedding_model:
            logger.warning("No embedding model available, will use zero vectors")

        logger.info("PageProcessor initialized")

    def process_page(
        self,
        topics: List[Dict],
        source_url: str,
        source_domain: Optional[str] = None
    ) -> Dict:
        """
        Process a single page: merge topics, generate embeddings, save to DB.

        Args:
            topics: List of extracted topics from TopicExtractor
            source_url: URL of the source page
            source_domain: Domain name (extracted from URL if not provided)

        Returns:
            Dict with processing statistics
        """
        logger.info(f"Processing page: {source_url}")
        logger.info(f"  Topics: {len(topics)}")

        if not topics:
            logger.warning("No topics to process")
            return {
                'topics_count': 0,
                'documents_created': 0,
                'documents_saved': 0,
                'error': 'No topics provided'
            }

        # Extract domain if not provided
        if not source_domain:
            from urllib.parse import urlparse
            source_domain = urlparse(source_url).netloc

        # Step 1: Merge topics into documents (DUAL-MODE: creates both full_doc and paragraph)
        logger.info("Step 1: Merging topics into documents (dual-mode)...")
        documents = self.merger.merge_topics_dual_mode(topics)
        merge_stats = self.merger.get_merge_statistics(documents)

        logger.info(f"  Created {len(documents)} documents:")
        logger.info(f"    Merged: {merge_stats['merged_documents']}")
        logger.info(f"    Standalone: {merge_stats['standalone_documents']}")

        # Step 2: Generate embeddings
        logger.info("Step 2: Generating embeddings...")
        documents_with_embeddings = self._generate_embeddings(documents)

        # Step 3: Save to database
        logger.info("Step 3: Saving to database...")
        saved_count = self._save_to_database(
            documents_with_embeddings,
            source_url,
            source_domain
        )

        logger.info(f"Processing complete: {saved_count} documents saved")

        return {
            'topics_count': len(topics),
            'documents_created': len(documents),
            'documents_saved': saved_count,
            'merge_stats': merge_stats,
            'source_url': source_url,
            'source_domain': source_domain
        }

    def _generate_embeddings(self, documents: List[Dict]) -> List[Dict]:
        """
        Generate embeddings for documents.

        Args:
            documents: List of documents from DocumentMerger

        Returns:
            Documents with 'embedding' field added
        """
        if not self.embedding_model:
            logger.warning(f"Embedding model not available, using zero vectors ({self.embedding_dimension or 768}D)")
            dim = self.embedding_dimension or 768
            for doc in documents:
                if NUMPY_AVAILABLE:
                    doc['embedding'] = np.zeros(dim).tolist()
                else:
                    doc['embedding'] = [0.0] * dim
            return documents

        logger.info(f"Generating embeddings for {len(documents)} documents using {self.embedding_provider}...")

        for i, doc in enumerate(documents, 1):
            # Create embedding text from title + content preview
            title = doc['title']
            # Get first 500 chars of content as preview
            content_preview = doc['content'][:500]
            embedding_text = f"{title}. {content_preview}"

            # Generate embedding based on provider
            if self.embedding_provider == "gemini":
                # Gemini API
                embedding = self.embedding_model.embed_text(embedding_text)
                doc['embedding'] = embedding

            elif self.embedding_provider == "sentence-transformers":
                # Sentence transformers
                embedding = self.embedding_model.encode(embedding_text, show_progress_bar=False)
                doc['embedding'] = embedding.tolist()

            logger.info(f"  [{i}/{len(documents)}] Generated embedding for: {title}")

        return documents

    def _save_to_database(
        self,
        documents: List[Dict],
        source_url: str,
        source_domain: str
    ) -> int:
        """
        Save documents to PostgreSQL database.

        Args:
            documents: Documents with embeddings
            source_url: Source URL
            source_domain: Source domain

        Returns:
            Number of documents saved
        """
        if not PSYCOPG2_AVAILABLE:
            logger.warning("psycopg2 not available, cannot save to database")
            return 0

        if not documents:
            return 0

        conn = None
        saved_count = 0

        try:
            # Connect to database
            logger.info(f"Connecting to database: {self.db_config['database']}")
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # Save each document
            for doc in documents:
                try:
                    # Extract keywords from source topics
                    keywords = []
                    for topic_title in doc['source_topics']:
                        # Simple keyword extraction: split on spaces, lowercase
                        words = topic_title.lower().split()
                        keywords.extend(words)

                    # Remove duplicates
                    keywords = list(set(keywords))[:10]  # Limit to 10 keywords

                    # Determine content_type based on document stats
                    if doc['stats']['token_count'] <= 2000:
                        content_type = 'quick_guide'
                    elif doc['stats']['token_count'] <= 8000:
                        content_type = 'tutorial'
                    else:
                        content_type = 'reference'

                    # Insert document
                    cursor.execute("""
                        INSERT INTO documents (
                            topic_title,
                            topic_summary,
                            content,
                            embedding,
                            category,
                            keywords,
                            source_domain,
                            content_type,
                            mode,
                            word_count
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        RETURNING id
                    """, (
                        doc['title'],
                        f"Merged from {len(doc['source_topics'])} topics. "
                        f"{doc['stats']['token_count']} tokens, "
                        f"{doc['stats']['mode']} mode.",
                        doc['content'],
                        doc['embedding'],
                        doc['category'],
                        keywords,
                        source_domain,
                        content_type,
                        doc.get('mode', doc['stats']['mode']),  # Use mode from document
                        doc['stats']['token_count'] // 1.12  # Approximate word count
                    ))

                    document_id = cursor.fetchone()[0]

                    # Insert source tracking
                    cursor.execute("""
                        INSERT INTO document_sources (
                            document_id,
                            source_url,
                            content_delta
                        ) VALUES (
                            %s, %s, %s
                        )
                    """, (
                        document_id,
                        source_url,
                        f"Contributed {len(doc['source_topics'])} topics: {', '.join(doc['source_topics'][:3])}..."
                    ))

                    saved_count += 1
                    logger.info(f"  Saved document: {doc['title']} (ID: {document_id})")

                except Exception as e:
                    logger.error(f"  Failed to save document {doc['title']}: {e}")
                    conn.rollback()
                    continue

            # Commit transaction
            conn.commit()
            logger.info(f"Successfully saved {saved_count} documents to database")

        except Exception as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()

        finally:
            if conn:
                cursor.close()
                conn.close()

        return saved_count

    def get_database_stats(self) -> Dict:
        """
        Get statistics from the database.

        Returns:
            Dict with database statistics
        """
        if not PSYCOPG2_AVAILABLE:
            logger.warning("psycopg2 not available, cannot get database stats")
            return {}

        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # Get overall stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total_documents,
                    COUNT(DISTINCT category) as total_categories,
                    SUM(word_count) as total_words,
                    AVG(word_count) as avg_words_per_doc
                FROM documents
            """)

            row = cursor.fetchone()
            stats = {
                'total_documents': row[0],
                'total_categories': row[1],
                'total_words': row[2],
                'avg_words_per_doc': row[3]
            }

            # Get category breakdown
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM documents
                WHERE category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC
            """)

            stats['categories'] = {row[0]: row[1] for row in cursor.fetchall()}

            return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

        finally:
            if conn:
                cursor.close()
                conn.close()


if __name__ == "__main__":
    # Quick test
    print("PageProcessor Test")
    print("=" * 80)

    # Test without database (dry run)
    processor = PageProcessor()

    # Create test topics
    test_topics = [
        {
            'title': 'Password Security Best Practices',
            'summary': 'Password tips',
            'category': 'security',
            'content': '''Strong passwords should be at least 12 characters long.
            Use a mix of uppercase, lowercase, numbers and symbols. Never reuse
            passwords across multiple accounts. Consider using a password manager
            like 1Password or Bitwarden.'''
        },
        {
            'title': 'Two-Factor Authentication Setup',
            'summary': '2FA guide',
            'category': 'security',
            'content': '''Enable 2FA on all accounts. Use authenticator apps instead
            of SMS when possible. Save backup codes in a secure location. Never
            share 2FA codes with anyone.'''
        },
        {
            'title': 'Hardware Wallet Guide',
            'summary': 'Hardware wallet setup',
            'category': 'wallet',
            'content': '''Hardware wallets provide the best security for cryptocurrency.
            Popular options include Ledger and Trezor. Always buy directly from the
            manufacturer. Never enter your seed phrase anywhere except the device itself.'''
        }
    ]

    # Merge topics (without saving to DB)
    documents = processor.merger.merge_topics(test_topics)
    stats = processor.merger.get_merge_statistics(documents)

    print(f"\n📊 Processing Results:")
    print(f"  Input: {len(test_topics)} topics")
    print(f"  Output: {len(documents)} documents")
    print(f"  Merged: {stats['merged_documents']}")
    print(f"  Standalone: {stats['standalone_documents']}")

    print(f"\n📝 Documents Created:")
    for i, doc in enumerate(documents, 1):
        print(f"\n{i}. {doc['title']}")
        print(f"   Category: {doc['category']}")
        print(f"   Type: {doc['type']}")
        print(f"   Source topics: {len(doc['source_topics'])}")
        print(f"   Tokens: {doc['stats']['token_count']}")
        print(f"   Sections: {doc['stats']['section_count']}")
        print(f"   Mode: {doc['stats']['mode']}")

    print("\n" + "=" * 80)
    print("✅ PageProcessor test complete!")
    print("\nNote: Database save skipped (test mode)")
