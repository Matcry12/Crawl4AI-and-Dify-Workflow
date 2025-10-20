#!/usr/bin/env python3
"""
Document Vector Database Module

Stores documents with embeddings for similarity search.
Supports both creating new documents and updating existing ones.
"""

import os

# Suppress gRPC warnings (must be set BEFORE importing genai)
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

import json
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import google.generativeai as genai


class DocumentDatabase:
    """
    Vector database for storing documents with embeddings
    """

    def __init__(self, db_path: str = "documents.db", api_key: str = None):
        """
        Initialize document database

        Args:
            db_path: Path to SQLite database file
            api_key: Gemini API key for creating embeddings
        """
        self.db_path = db_path
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Please set it in .env file")

        genai.configure(api_key=self.api_key)

        # Initialize database
        self._init_database()

        print("✅ Document database initialized")
        print(f"   Database: {db_path}")

    def _init_database(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT,
                mode TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                metadata TEXT
            )
        """)

        # Merged topics tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merged_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                topic_title TEXT NOT NULL,
                merged_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            )
        """)

        # Create index for faster searches
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_mode
            ON documents(mode)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_category
            ON documents(category)
        """)

        conn.commit()
        conn.close()

    def create_embedding(self, text: str) -> List[float]:
        """
        Create embedding for text using Gemini

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"  ❌ Embedding error: {e}")
            return None

    def generate_document_id(self, title: str, mode: str) -> str:
        """
        Generate unique document ID

        Args:
            title: Document title
            mode: Document mode (paragraph/full-doc)

        Returns:
            Document ID
        """
        # Create safe ID from title and mode
        safe_title = "".join(c if c.isalnum() else '_' for c in title.lower())
        return f"{safe_title}_{mode}"

    def insert_document(self, document: Dict) -> bool:
        """
        Insert new document into database

        Args:
            document: Document dictionary with title, category, mode, content

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate ID
            doc_id = self.generate_document_id(document['title'], document['mode'])

            # Create embedding from content
            print(f"  📊 Creating embedding for: {document['title']} ({document['mode']})")
            embedding = self.create_embedding(document['content'])

            if not embedding:
                print(f"  ❌ Failed to create embedding")
                return False

            # Convert embedding to JSON string for storage
            embedding_json = json.dumps(embedding)

            # Prepare metadata
            metadata = {
                'source_topic': document.get('source_topic', {}),
                'merged_topics': document.get('merged_topics', [])
            }
            metadata_json = json.dumps(metadata)

            # Insert into database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO documents (id, title, category, mode, content, embedding, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                document['title'],
                document['category'],
                document['mode'],
                document['content'],
                embedding_json,
                document.get('created_at', datetime.now().isoformat()),
                document.get('updated_at'),
                metadata_json
            ))

            conn.commit()
            conn.close()

            print(f"  ✅ Document inserted: {doc_id}")
            return True

        except sqlite3.IntegrityError:
            print(f"  ⚠️  Document already exists: {doc_id}")
            return False
        except Exception as e:
            print(f"  ❌ Insert error: {e}")
            return False

    def update_document(self, document: Dict) -> bool:
        """
        Update existing document in database

        Args:
            document: Document dictionary with title, mode, content, and merged_topics

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate ID
            doc_id = self.generate_document_id(document['title'], document['mode'])

            # Create new embedding from updated content
            print(f"  📊 Creating embedding for updated: {document['title']} ({document['mode']})")
            embedding = self.create_embedding(document['content'])

            if not embedding:
                print(f"  ❌ Failed to create embedding")
                return False

            # Convert embedding to JSON string
            embedding_json = json.dumps(embedding)

            # Prepare updated metadata
            metadata = {
                'merged_topics': document.get('merged_topics', [])
            }
            metadata_json = json.dumps(metadata)

            # Update document
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE documents
                SET content = ?, embedding = ?, updated_at = ?, metadata = ?
                WHERE id = ?
            """, (
                document['content'],
                embedding_json,
                document.get('updated_at', datetime.now().isoformat()),
                metadata_json,
                doc_id
            ))

            # Add merged topic tracking
            if 'merged_topics' in document and document['merged_topics']:
                for topic in document['merged_topics']:
                    cursor.execute("""
                        INSERT INTO merged_topics (document_id, topic_title, merged_at)
                        VALUES (?, ?, ?)
                    """, (doc_id, topic['title'], topic['merged_at']))

            conn.commit()
            conn.close()

            print(f"  ✅ Document updated: {doc_id}")
            return True

        except Exception as e:
            print(f"  ❌ Update error: {e}")
            return False

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """
        Retrieve document by ID

        Args:
            doc_id: Document ID

        Returns:
            Document dictionary or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, title, category, mode, content, embedding, created_at, updated_at, metadata
                FROM documents
                WHERE id = ?
            """, (doc_id,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return {
                'id': row[0],
                'title': row[1],
                'category': row[2],
                'mode': row[3],
                'content': row[4],
                'embedding': json.loads(row[5]),
                'created_at': row[6],
                'updated_at': row[7],
                'metadata': json.loads(row[8]) if row[8] else {}
            }

        except Exception as e:
            print(f"  ❌ Get error: {e}")
            return None

    def get_all_documents(self, mode: Optional[str] = None) -> List[Dict]:
        """
        Get all documents, optionally filtered by mode

        Args:
            mode: Optional mode filter ("paragraph" or "full-doc")

        Returns:
            List of document dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if mode:
                cursor.execute("""
                    SELECT id, title, category, mode, content, embedding, created_at, updated_at, metadata
                    FROM documents
                    WHERE mode = ?
                """, (mode,))
            else:
                cursor.execute("""
                    SELECT id, title, category, mode, content, embedding, created_at, updated_at, metadata
                    FROM documents
                """)

            rows = cursor.fetchall()
            conn.close()

            documents = []
            for row in rows:
                documents.append({
                    'id': row[0],
                    'title': row[1],
                    'category': row[2],
                    'mode': row[3],
                    'content': row[4],
                    'embedding': json.loads(row[5]),
                    'created_at': row[6],
                    'updated_at': row[7],
                    'metadata': json.loads(row[8]) if row[8] else {}
                })

            return documents

        except Exception as e:
            print(f"  ❌ Get all error: {e}")
            return []

    def search_similar_documents(
        self,
        query_embedding: List[float],
        mode: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search for similar documents using embedding similarity

        Args:
            query_embedding: Query embedding vector
            mode: Optional mode filter
            limit: Maximum number of results

        Returns:
            List of similar documents with similarity scores
        """
        # Get all documents (filtered by mode if specified)
        documents = self.get_all_documents(mode)

        if not documents:
            return []

        # Calculate similarities
        import math

        results = []
        for doc in documents:
            doc_embedding = doc['embedding']

            # Cosine similarity
            dot_product = sum(a * b for a, b in zip(query_embedding, doc_embedding))
            magnitude1 = math.sqrt(sum(a * a for a in query_embedding))
            magnitude2 = math.sqrt(sum(b * b for b in doc_embedding))

            if magnitude1 == 0 or magnitude2 == 0:
                similarity = 0.0
            else:
                similarity = dot_product / (magnitude1 * magnitude2)

            results.append({
                'document': doc,
                'similarity': similarity
            })

        # Sort by similarity (highest first)
        results.sort(key=lambda x: x['similarity'], reverse=True)

        # Return top N results
        return results[:limit]

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete document by ID

        Args:
            doc_id: Document ID

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Delete merged topics first
            cursor.execute("DELETE FROM merged_topics WHERE document_id = ?", (doc_id,))

            # Delete document
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

            conn.commit()
            conn.close()

            print(f"  ✅ Document deleted: {doc_id}")
            return True

        except Exception as e:
            print(f"  ❌ Delete error: {e}")
            return False

    def get_statistics(self) -> Dict:
        """
        Get database statistics

        Returns:
            Statistics dictionary
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Total documents
            cursor.execute("SELECT COUNT(*) FROM documents")
            total = cursor.fetchone()[0]

            # Documents by mode
            cursor.execute("SELECT mode, COUNT(*) FROM documents GROUP BY mode")
            by_mode = dict(cursor.fetchall())

            # Documents by category
            cursor.execute("SELECT category, COUNT(*) FROM documents GROUP BY category")
            by_category = dict(cursor.fetchall())

            # Total merged topics
            cursor.execute("SELECT COUNT(*) FROM merged_topics")
            merged_count = cursor.fetchone()[0]

            conn.close()

            return {
                'total_documents': total,
                'by_mode': by_mode,
                'by_category': by_category,
                'total_merged': merged_count
            }

        except Exception as e:
            print(f"  ❌ Statistics error: {e}")
            return {}

    def print_statistics(self):
        """Print database statistics"""
        stats = self.get_statistics()

        print(f"\n{'='*80}")
        print("📊 DATABASE STATISTICS")
        print(f"{'='*80}")
        print(f"\nTotal documents: {stats.get('total_documents', 0)}")

        if stats.get('by_mode'):
            print(f"\nBy mode:")
            for mode, count in stats['by_mode'].items():
                print(f"   {mode}: {count}")

        if stats.get('by_category'):
            print(f"\nBy category:")
            for category, count in stats['by_category'].items():
                print(f"   {category}: {count}")

        print(f"\nTotal merges: {stats.get('total_merged', 0)}")
        print(f"{'='*80}")


# Example usage and testing
async def main():
    """Test document database"""
    print("="*80)
    print("📊 Document Database Test")
    print("="*80)

    # Initialize database
    try:
        db = DocumentDatabase(db_path="test_documents.db")
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        return

    # Test 1: Insert new documents
    print("\n" + "="*80)
    print("TEST 1: INSERT DOCUMENTS")
    print("="*80)

    doc1_para = {
        "title": "Python Bug Reporting",
        "category": "guide",
        "mode": "paragraph",
        "content": "To report bugs in Python, use the GitHub issues tracker at https://github.com/python/cpython/issues. Search existing issues first to avoid duplicates.",
        "created_at": datetime.now().isoformat()
    }

    doc1_full = {
        "title": "Python Bug Reporting",
        "category": "guide",
        "mode": "full-doc",
        "content": "## Overview\n\nThe Python bug reporting system uses GitHub Issues.\n\n## How to Report\n\nVisit the tracker and create a new issue with detailed information.",
        "created_at": datetime.now().isoformat()
    }

    db.insert_document(doc1_para)
    db.insert_document(doc1_full)

    # Test 2: Update document (merge scenario)
    print("\n" + "="*80)
    print("TEST 2: UPDATE DOCUMENT (MERGE)")
    print("="*80)

    updated_doc = {
        "title": "Python Bug Reporting",
        "mode": "paragraph",
        "content": "To report bugs in Python, use the GitHub issues tracker at https://github.com/python/cpython/issues. Search existing issues first to avoid duplicates. Include platform details: Python version, OS, and hardware architecture. Anonymous reports are not allowed.",
        "updated_at": datetime.now().isoformat(),
        "merged_topics": [
            {
                "title": "Additional Bug Info",
                "merged_at": datetime.now().isoformat()
            }
        ]
    }

    db.update_document(updated_doc)

    # Test 3: Retrieve document
    print("\n" + "="*80)
    print("TEST 3: RETRIEVE DOCUMENT")
    print("="*80)

    doc_id = db.generate_document_id("Python Bug Reporting", "paragraph")
    retrieved = db.get_document(doc_id)

    if retrieved:
        print(f"  Retrieved: {retrieved['title']}")
        print(f"  Mode: {retrieved['mode']}")
        print(f"  Content length: {len(retrieved['content'])} chars")
        print(f"  Embedding dimensions: {len(retrieved['embedding'])}")
        print(f"  Updated: {retrieved['updated_at']}")

    # Test 4: Statistics
    print("\n" + "="*80)
    print("TEST 4: STATISTICS")
    print("="*80)

    db.print_statistics()

    # Test 5: Search similar documents
    print("\n" + "="*80)
    print("TEST 5: SIMILARITY SEARCH")
    print("="*80)

    # Create query embedding
    query_text = "How to submit bug reports for Python"
    print(f"\nQuery: {query_text}")
    query_embedding = db.create_embedding(query_text)

    if query_embedding:
        results = db.search_similar_documents(query_embedding, limit=3)

        print(f"\nTop {len(results)} similar documents:")
        for i, result in enumerate(results, 1):
            doc = result['document']
            similarity = result['similarity']
            print(f"\n{i}. {doc['title']} ({doc['mode']})")
            print(f"   Similarity: {similarity:.3f}")
            print(f"   Category: {doc['category']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
