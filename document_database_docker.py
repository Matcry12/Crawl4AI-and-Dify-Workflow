#!/usr/bin/env python3
"""
PostgreSQL Document Database - Docker Wrapper
Executes database operations inside the Docker container
"""

import os
import json
import subprocess
from typing import List, Dict, Optional, Any


class DocumentDatabaseDocker:
    """
    Wrapper for PostgreSQL database operations using docker exec

    This allows us to use PostgreSQL without exposing ports
    """

    def __init__(
        self,
        container_name: str = "docker-db-1",
        database: str = "crawl4ai",
        user: str = "postgres"
    ):
        """
        Initialize Docker database wrapper

        Args:
            container_name: Docker container name
            database: Database name
            user: Database user
        """
        self.container_name = container_name
        self.database = database
        self.user = user

        # Verify container is running
        self._verify_container()
        print(f"✅ PostgreSQL database initialized")
        print(f"   Container: {container_name}")
        print(f"   Database: {database}")

    def _verify_container(self):
        """Verify Docker container is running"""
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", self.container_name],
                capture_output=True,
                text=True,
                check=True
            )
            if result.stdout.strip() != "true":
                raise RuntimeError(f"Container {self.container_name} is not running")
        except subprocess.CalledProcessError:
            raise RuntimeError(f"Container {self.container_name} not found")

    def _execute_sql(self, sql: str, return_dicts: bool = True) -> Any:
        """
        Execute SQL query in Docker container

        Args:
            sql: SQL query (should NOT have quotes pre-escaped)
            return_dicts: Return as list of dicts (otherwise raw output)

        Returns:
            Query results
        """
        # Don't escape here - SQL should already be properly formed

        if return_dicts:
            # With headers for dict parsing
            cmd = [
                "docker", "exec", self.container_name,
                "psql", "-U", self.user, "-d", self.database,
                "-A", "-F", "|",  # Unaligned, pipe separator (keeps headers)
                "-c", sql
            ]
        else:
            # Tuples only
            cmd = [
                "docker", "exec", self.container_name,
                "psql", "-U", self.user, "-d", self.database,
                "-t", "-A",  # Tuples only, unaligned
                "-c", sql
            ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            if not return_dicts:
                return result.stdout.strip()

            # Parse result as dicts
            lines = result.stdout.strip().split('\n')
            if not lines or not lines[0]:
                return []

            # First line is header (column names)
            if '|' in lines[0]:
                headers = lines[0].split('|')
                rows = []
                for line in lines[1:]:
                    if line.strip() and not line.startswith('('):  # Skip row count line
                        values = line.split('|')
                        row = dict(zip(headers, values))
                        rows.append(row)
                return rows
            else:
                # Single column result
                header = lines[0]
                return [{header: line} for line in lines[1:] if line.strip() and not line.startswith('(')]

        except subprocess.CalledProcessError as e:
            print(f"❌ SQL Error: {e.stderr}")
            return [] if return_dicts else ""

    def create_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        category: Optional[str] = None,
        mode: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Create a new document"""
        # Escape strings
        title = title.replace("'", "''")
        content = content.replace("'", "''")

        # Build embedding string
        emb_str = "NULL"
        if embedding:
            emb_str = f"ARRAY{embedding}::vector"

        # Build metadata string
        meta_str = "'{}'::jsonb"
        if metadata:
            meta_json = json.dumps(metadata).replace("'", "''")
            meta_str = f"'{meta_json}'::jsonb"

        sql = f"""
            INSERT INTO documents (id, title, content, category, mode, embedding, metadata)
            VALUES ('{doc_id}', '{title}', '{content}',
                    {'NULL' if not category else f"'{category}'"},
                    {'NULL' if not mode else f"'{mode}'"},
                    {emb_str}, {meta_str})
            ON CONFLICT (id) DO UPDATE
            SET title = EXCLUDED.title,
                content = EXCLUDED.content,
                category = EXCLUDED.category,
                mode = EXCLUDED.mode,
                embedding = COALESCE(EXCLUDED.embedding, documents.embedding),
                metadata = EXCLUDED.metadata,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id;
        """

        result = self._execute_sql(sql)
        return len(result) > 0

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get document by ID"""
        sql = f"""
            SELECT id, title, category, mode, content, metadata,
                   created_at, updated_at
            FROM documents
            WHERE id = '{doc_id}';
        """

        result = self._execute_sql(sql)
        return result[0] if result else None

    def list_documents(
        self,
        mode: Optional[str] = None,
        category: Optional[str] = None,
        limit: Optional[int] = None,
        include_embeddings: bool = True
    ) -> List[Dict]:
        """
        List documents with optional filters

        Args:
            mode: Filter by mode
            category: Filter by category
            limit: Maximum results
            include_embeddings: Include embedding vectors (default True)
        """
        conditions = []

        if mode:
            conditions.append(f"mode = '{mode}'")

        if category:
            conditions.append(f"category = '{category}'")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        limit_clause = f"LIMIT {limit}" if limit else ""

        # Include embedding if requested
        embedding_col = "embedding::text as embedding_str" if include_embeddings else ""
        select_cols = "id, title, category, mode, content, created_at, updated_at"
        if embedding_col:
            select_cols += f", {embedding_col}"

        sql = f"""
            SELECT {select_cols}
            FROM documents
            {where_clause}
            ORDER BY created_at DESC
            {limit_clause};
        """

        results = self._execute_sql(sql)

        # Parse embeddings from string format if included
        if include_embeddings and results:
            for doc in results:
                if 'embedding_str' in doc and doc['embedding_str']:
                    # Parse PostgreSQL array format: [0.1,0.2,0.3,...] → list of floats
                    emb_str = doc['embedding_str']
                    if emb_str and emb_str != '':
                        try:
                            # Remove brackets and split by comma
                            emb_str = emb_str.strip('[]')
                            doc['embedding'] = [float(x) for x in emb_str.split(',')]
                        except:
                            doc['embedding'] = None
                    else:
                        doc['embedding'] = None
                    # Remove the temporary string field
                    del doc['embedding_str']
                else:
                    doc['embedding'] = None

        return results

    def search_similar_documents(
        self,
        query_embedding: List[float],
        mode: Optional[str] = None,
        limit: int = 5,
        min_similarity: float = 0.0
    ) -> List[Dict]:
        """Search similar documents using vector similarity"""
        conditions = []

        if mode:
            conditions.append(f"mode = '{mode}'")

        where_clause = f"AND {' AND '.join(conditions)}" if conditions else ""

        # Convert embedding to PostgreSQL array
        emb_array = f"ARRAY{query_embedding}::vector"

        sql = f"""
            SELECT id, title, category, mode,
                   (1 - (embedding <=> {emb_array})) AS similarity
            FROM documents
            WHERE embedding IS NOT NULL
              AND (1 - (embedding <=> {emb_array})) >= {min_similarity}
              {where_clause}
            ORDER BY embedding <=> {emb_array}
            LIMIT {limit};
        """

        return self._execute_sql(sql)

    def delete_document(self, doc_id: str) -> bool:
        """Delete document"""
        sql = f"DELETE FROM documents WHERE id = '{doc_id}' RETURNING id;"
        result = self._execute_sql(sql)
        return len(result) > 0

    def get_statistics(self) -> Dict:
        """Get database statistics"""
        # Total documents
        result = self._execute_sql("SELECT COUNT(*) as total FROM documents;")
        total_docs = int(result[0]['total']) if result else 0

        # Documents with embeddings
        result = self._execute_sql("""
            SELECT COUNT(*) as count
            FROM documents
            WHERE embedding IS NOT NULL;
        """)
        docs_with_embeddings = int(result[0]['count']) if result else 0

        # By category
        result = self._execute_sql("""
            SELECT category, COUNT(*) as count
            FROM documents
            GROUP BY category
            ORDER BY count DESC;
        """)
        by_category = {row['category']: int(row['count']) for row in result if result}

        # By mode
        result = self._execute_sql("""
            SELECT mode, COUNT(*) as count
            FROM documents
            GROUP BY mode
            ORDER BY count DESC;
        """)
        by_mode = {row['mode']: int(row['count']) for row in result if result}

        return {
            "total_documents": total_docs,
            "documents_with_embeddings": docs_with_embeddings,
            "by_category": by_category,
            "by_mode": by_mode,
            "embedding_percentage": (
                docs_with_embeddings / total_docs * 100
                if total_docs > 0 else 0
            )
        }


# Example usage
def main():
    """Test Docker database wrapper"""
    print("=" * 80)
    print("🐘 PostgreSQL Document Database Test (Docker)")
    print("=" * 80)

    # Initialize database
    db = DocumentDatabaseDocker()

    # Get statistics
    stats = db.get_statistics()
    print(f"\n📊 Database Statistics:")
    print(f"   Total documents: {stats['total_documents']}")
    print(f"   With embeddings: {stats['documents_with_embeddings']}")
    print(f"   Embedding coverage: {stats['embedding_percentage']:.1f}%")

    if stats['by_category']:
        print(f"\n📁 By Category:")
        for category, count in stats['by_category'].items():
            print(f"   {category}: {count}")

    if stats['by_mode']:
        print(f"\n🔧 By Mode:")
        for mode, count in stats['by_mode'].items():
            print(f"   {mode}: {count}")

    print("\n" + "=" * 80)
    print("✅ Database test complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
