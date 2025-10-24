#!/usr/bin/env python3
"""
Chunked Document Database Module (PostgreSQL via Docker)

Stores documents with 3-level hierarchical chunking:
- Level 1: Document (with summary embedding)
- Level 2: Semantic sections (200-400 tokens)
- Level 3: Semantic propositions (50-150 tokens)

Uses docker exec for all database operations (no port exposure needed)
"""

import os
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

import subprocess
import json
import tempfile
from typing import List, Dict, Optional
from datetime import datetime


class ChunkedDocumentDatabase:
    """
    PostgreSQL database for storing hierarchically chunked documents
    Uses docker exec to connect (no port exposure needed)
    """

    def __init__(
        self,
        container_name: str = None,
        database: str = None,
        user: str = "postgres"
    ):
        """
        Initialize chunked document database

        Args:
            container_name: Docker container name (defaults to POSTGRES_CONTAINER env var)
            database: Database name (defaults to POSTGRES_DATABASE env var)
            user: Database user
        """
        self.container_name = container_name or os.getenv('POSTGRES_CONTAINER', 'postgres-crawl4ai')
        self.database = database or os.getenv('POSTGRES_DATABASE', 'crawl4ai')
        self.user = user

        # Verify container is running
        self._verify_container()

        print("✅ Chunked document database initialized")
        print(f"   Container: {self.container_name}")
        print(f"   Database: {self.database}")
        print(f"   Schema: 3-level hierarchy (doc → sections → propositions)")

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

    def _execute_sql_file(self, sql_content: str) -> bool:
        """
        Execute SQL from a temporary file via docker exec

        Args:
            sql_content: SQL commands to execute

        Returns:
            True if successful, False otherwise
        """
        temp_file = None
        try:
            # Write SQL to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
                f.write(sql_content)
                temp_file = f.name

            # Copy file to container
            subprocess.run(
                ["docker", "cp", temp_file, f"{self.container_name}:/tmp/temp_query.sql"],
                check=True,
                capture_output=True
            )

            # Execute SQL file in container with ON_ERROR_STOP
            # This makes psql exit with non-zero code on any error
            result = subprocess.run(
                ["docker", "exec", self.container_name,
                 "psql", "-U", self.user, "-d", self.database,
                 "-v", "ON_ERROR_STOP=1",
                 "-f", "/tmp/temp_query.sql"],
                capture_output=True,
                text=True,
                check=False  # Don't raise exception, we'll check manually
            )

            # Check for errors in output
            has_error = False
            if result.returncode != 0:
                has_error = True
                print(f"  ❌ psql exited with code {result.returncode}")

            # Also check for ERROR in output (belt and suspenders)
            if "ERROR:" in result.stderr or "ERROR:" in result.stdout:
                has_error = True
                print(f"  ❌ SQL execution errors detected:")
                if result.stderr:
                    print(f"     stderr: {result.stderr[:500]}")
                if result.stdout:
                    print(f"     stdout: {result.stdout[:500]}")

            # Clean up
            os.unlink(temp_file)
            subprocess.run(
                ["docker", "exec", self.container_name, "rm", "/tmp/temp_query.sql"],
                capture_output=True
            )

            if has_error:
                return False

            return True

        except subprocess.CalledProcessError as e:
            print(f"  ❌ SQL Error: {e.stderr}")
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)
            return False
        except Exception as e:
            print(f"  ❌ Error: {e}")
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)
            return False

    def insert_document(self, document: Dict) -> bool:
        """
        Insert document with full hierarchy

        Args:
            document: Document dict with 'chunks' key containing hierarchical chunks

        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract data
            doc_id = document['id']
            title = document['title']
            category = document.get('category', 'general')
            mode = document['mode']
            content = document['content']
            chunks = document.get('chunks')

            if not chunks:
                print(f"  ⚠️  Document {doc_id} has no chunks, storing document only")
                # Just store basic document
                sql = f"""
INSERT INTO documents (id, title, category, mode, content, created_at)
VALUES (
    {self._quote(doc_id)},
    {self._quote(title)},
    {self._quote(category)},
    {self._quote(mode)},
    {self._quote(content)},
    CURRENT_TIMESTAMP
)
ON CONFLICT (id) DO UPDATE SET
    content = EXCLUDED.content,
    updated_at = CURRENT_TIMESTAMP;
"""
                return self._execute_sql_file(sql)

            # Build complete SQL for document + chunks
            sql_parts = []

            # 1. Insert document with summary
            summary = chunks['summary']
            sql_parts.append(f"""
INSERT INTO documents (id, title, category, mode, content, summary, created_at)
VALUES (
    {self._quote(doc_id)},
    {self._quote(title)},
    {self._quote(category)},
    {self._quote(mode)},
    {self._quote(content)},
    {self._quote(summary)},
    CURRENT_TIMESTAMP
)
ON CONFLICT (id) DO UPDATE SET
    content = EXCLUDED.content,
    summary = EXCLUDED.summary,
    updated_at = CURRENT_TIMESTAMP;
""")

            # 2. Insert document summary embedding
            summary_embedding_vec = self._quote_vector(chunks['summary_embedding'])
            sql_parts.append(f"""
INSERT INTO embeddings (entity_type, entity_id, embedding)
VALUES ('document_summary', {self._quote(doc_id)}, {summary_embedding_vec})
ON CONFLICT (entity_type, entity_id) DO UPDATE SET embedding = EXCLUDED.embedding;
""")

            # 3. Insert sections and propositions
            for section in chunks['sections']:
                section_id = section['section_id']
                section_index = section['section_index']
                header = section.get('header', '')
                section_content = section['content']
                token_count = section['token_count']
                keywords = section.get('keywords', [])
                topics = section.get('topics', [])
                section_type = section.get('section_type', '')

                # Insert section
                keywords_array = self._array(keywords)
                topics_array = self._array(topics)
                sql_parts.append(f"""
INSERT INTO semantic_sections (
    id, document_id, section_index, header, content,
    token_count, keywords, topics, section_type
)
VALUES (
    {self._quote(section_id)},
    {self._quote(doc_id)},
    {section_index},
    {self._quote(header) if header else 'NULL'},
    {self._quote(section_content)},
    {token_count},
    {keywords_array},
    {topics_array},
    {self._quote(section_type) if section_type else 'NULL'}
)
ON CONFLICT (document_id, section_index) DO UPDATE SET
    content = EXCLUDED.content,
    header = EXCLUDED.header,
    token_count = EXCLUDED.token_count,
    keywords = EXCLUDED.keywords,
    topics = EXCLUDED.topics,
    section_type = EXCLUDED.section_type;
""")

                # Insert section embedding
                section_embedding_vec = self._quote_vector(section['embedding'])
                sql_parts.append(f"""
INSERT INTO embeddings (entity_type, entity_id, embedding)
VALUES ('section', {self._quote(section_id)}, {section_embedding_vec})
ON CONFLICT (entity_type, entity_id) DO UPDATE SET embedding = EXCLUDED.embedding;
""")

                # Insert propositions
                for prop in section['propositions']:
                    prop_id = prop['proposition_id']
                    prop_index = prop['proposition_index']
                    prop_content = prop['content']
                    prop_token_count = prop['token_count']
                    prop_type = prop.get('proposition_type', '')
                    entities = prop.get('entities', [])
                    prop_keywords = prop.get('keywords', [])

                    entities_array = self._array(entities)
                    prop_keywords_array = self._array(prop_keywords)

                    sql_parts.append(f"""
INSERT INTO semantic_propositions (
    id, section_id, proposition_index, content,
    token_count, proposition_type, entities, keywords
)
VALUES (
    {self._quote(prop_id)},
    {self._quote(section_id)},
    {prop_index},
    {self._quote(prop_content)},
    {prop_token_count},
    {self._quote(prop_type) if prop_type else 'NULL'},
    {entities_array},
    {prop_keywords_array}
)
ON CONFLICT (section_id, proposition_index) DO UPDATE SET
    content = EXCLUDED.content,
    token_count = EXCLUDED.token_count,
    proposition_type = EXCLUDED.proposition_type,
    entities = EXCLUDED.entities,
    keywords = EXCLUDED.keywords;
""")

                    # Insert proposition embedding
                    prop_embedding_vec = self._quote_vector(prop['embedding'])
                    sql_parts.append(f"""
INSERT INTO embeddings (entity_type, entity_id, embedding)
VALUES ('proposition', {self._quote(prop_id)}, {prop_embedding_vec})
ON CONFLICT (entity_type, entity_id) DO UPDATE SET embedding = EXCLUDED.embedding;
""")

            # Execute all SQL in one transaction
            # Build transaction with explicit error handling
            full_sql = "BEGIN;\n" + "\n".join(sql_parts) + "\nCOMMIT;"

            # Execute SQL
            success = self._execute_sql_file(full_sql)

            if not success:
                print(f"  ❌ Document insertion failed: {doc_id}")
                print(f"     Sections: {len(chunks['sections'])}")
                print(f"     Propositions: {chunks['stats']['total_propositions']}")

                # Save failed SQL for debugging
                debug_file = f"/tmp/failed_insert_{doc_id}.sql"
                try:
                    with open(debug_file, 'w') as f:
                        f.write(full_sql)
                    print(f"     Debug SQL saved to: {debug_file}")
                except Exception as e:
                    print(f"     Could not save debug SQL: {e}")

                return False

            print(f"  ✅ Document inserted: {doc_id}")
            print(f"     Sections: {len(chunks['sections'])}")
            print(f"     Propositions: {chunks['stats']['total_propositions']}")
            return True

        except Exception as e:
            print(f"  ❌ Error inserting document: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _quote(self, value: str) -> str:
        """Quote and escape string for SQL"""
        if value is None:
            return "NULL"
        # Escape single quotes by doubling them
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"

    def _array(self, items: List[str]) -> str:
        """Convert list to PostgreSQL array"""
        if not items:
            return "ARRAY[]::text[]"
        quoted_items = [self._quote(item).strip("'") for item in items]
        array_str = "ARRAY[" + ",".join([f"'{item}'" for item in quoted_items]) + "]"
        return array_str

    def _quote_vector(self, embedding: List[float]) -> str:
        """
        Convert embedding list to PostgreSQL vector format

        Args:
            embedding: List of floats (768 dimensions)

        Returns:
            Formatted string like '[0.1,0.2,...]'::vector
        """
        if not embedding:
            return "NULL"

        # PostgreSQL vector format: [0.1,0.2,0.3,...]
        vec_str = '[' + ','.join(str(float(x)) for x in embedding) + ']'
        return f"'{vec_str}'::vector"

    def get_all_documents_with_embeddings(self, mode: str = None) -> List[Dict]:
        """
        Get all documents with their summary embeddings from database

        Args:
            mode: Optional filter by mode ('paragraph' or 'full-doc')

        Returns:
            List of dicts with id, title, mode, category, summary, and embedding
        """
        mode_filter = ""
        if mode:
            mode_filter = f"AND d.mode = '{mode}'"

        sql = f"""
        SELECT
            d.id,
            d.title,
            d.category,
            d.mode,
            d.summary,
            d.content,
            d.created_at,
            d.updated_at
        FROM documents d
        WHERE d.summary IS NOT NULL
        {mode_filter}
        ORDER BY d.created_at DESC;
        """

        try:
            # Use a unique record separator to handle multi-line content
            # Use ASCII 30 (record separator) as delimiter between rows
            result = subprocess.run(
                ["docker", "exec", self.container_name,
                 "psql", "-U", self.user, "-d", self.database,
                 "-t", "-A", "-F", "|||", "-R", "\x1e", "-c", sql],
                capture_output=True,
                text=True,
                check=True
            )

            documents = []
            # Split by record separator (handles multi-line content correctly)
            records = result.stdout.strip().split('\x1e')
            for record in records:
                if not record.strip():
                    continue
                parts = record.split('|||')
                if len(parts) >= 8:
                    doc_id, title, category, mode, summary, content, created_at, updated_at = parts[:8]

                    # Now get the embedding for this document
                    emb_sql = f"""
                    SELECT embedding::text
                    FROM embeddings
                    WHERE entity_type = 'document_summary' AND entity_id = '{doc_id}';
                    """

                    emb_result = subprocess.run(
                        ["docker", "exec", self.container_name,
                         "psql", "-U", self.user, "-d", self.database,
                         "-t", "-A", "-c", emb_sql],
                        capture_output=True,
                        text=True,
                        check=False
                    )

                    # Parse embedding from PostgreSQL vector format [0.1,0.2,...]
                    embedding = None
                    if emb_result.returncode == 0 and emb_result.stdout.strip():
                        emb_str = emb_result.stdout.strip()
                        # Remove brackets and split by comma
                        if emb_str.startswith('[') and emb_str.endswith(']'):
                            emb_str = emb_str[1:-1]
                            embedding = [float(x) for x in emb_str.split(',')]

                    documents.append({
                        'id': doc_id,
                        'title': title,
                        'category': category,
                        'mode': mode,
                        'summary': summary,
                        'content': content,
                        'embedding': embedding,
                        'created_at': created_at,
                        'updated_at': updated_at
                    })

            return documents

        except Exception as e:
            print(f"  ❌ Error fetching documents: {e}")
            return []

    def search_similar_documents(
        self,
        query_embedding: List[float],
        mode: str = None,
        limit: int = 10,
        min_similarity: float = 0.0
    ) -> List[Dict]:
        """
        Search for similar documents using PostgreSQL vector similarity

        This method uses PostgreSQL's native vector operations with the HNSW index
        for extremely fast similarity search (200-600x faster than Python).

        Args:
            query_embedding: Query embedding vector (768 dimensions)
            mode: Optional filter by mode ('paragraph' or 'full-doc')
            limit: Maximum number of results to return (default: 10)
            min_similarity: Minimum similarity score (0-1, default: 0.0)

        Returns:
            List of dicts with document info and similarity scores:
            [
                {
                    'id': 'doc_id',
                    'title': '...',
                    'category': '...',
                    'mode': '...',
                    'summary': '...',
                    'content': '...',
                    'embedding': [...],
                    'similarity': 0.95,
                    'created_at': datetime,
                    'updated_at': datetime
                }
            ]
        """
        try:
            # Build mode filter
            mode_filter = ""
            if mode:
                mode_filter = f"AND d.mode = '{mode}'"

            # Convert embedding to PostgreSQL vector format
            query_vec = self._quote_vector(query_embedding)

            # PostgreSQL cosine similarity: 1 - (embedding <=> query)
            # The <=> operator returns cosine distance (0 = identical, 2 = opposite)
            # Convert to similarity: similarity = 1 - (distance / 2)
            # Simplified: similarity = 1 - distance when distance is in [0, 2]
            # But pgvector already normalizes, so: similarity = 1 - distance
            sql = f"""
            SELECT
                d.id,
                d.title,
                d.category,
                d.mode,
                d.summary,
                d.content,
                d.created_at,
                d.updated_at,
                e.embedding,
                -- Cosine similarity (1 = identical, 0 = perpendicular, -1 = opposite)
                1 - (e.embedding <=> {query_vec}) AS similarity
            FROM documents d
            INNER JOIN embeddings e ON e.entity_type = 'document_summary' AND e.entity_id = d.id
            WHERE d.summary IS NOT NULL
            {mode_filter}
            AND (1 - (e.embedding <=> {query_vec})) >= {min_similarity}
            ORDER BY e.embedding <=> {query_vec}
            LIMIT {limit};
            """

            # Execute query using docker exec
            result = subprocess.run(
                ["docker", "exec", self.container_name,
                 "psql", "-U", self.user, "-d", self.database,
                 "-t",  # tuples only (no headers/footers)
                 "-c", sql],
                capture_output=True,
                text=True,
                check=False
            )

            # Check for errors
            if result.returncode != 0:
                print(f"  ❌ psql error: {result.stderr}")
                return []

            # Parse results
            documents = []
            if result.stdout and result.stdout.strip():
                lines = result.stdout.strip().split('\n')

                # Skip header and separator lines
                data_lines = [line for line in lines if line and '─' not in line and not line.startswith(' id ')]

                for line in data_lines:
                    # Skip empty lines
                    if not line.strip():
                        continue

                    parts = line.split('|')
                    if len(parts) >= 10:
                        try:
                            doc_id = parts[0].strip()
                            title = parts[1].strip()
                            category = parts[2].strip()
                            mode_val = parts[3].strip()
                            summary = parts[4].strip()
                            content = parts[5].strip()
                            created_at = parts[6].strip()
                            updated_at = parts[7].strip()
                            embedding_str = parts[8].strip()
                            similarity_str = parts[9].strip()

                            # Skip if essential fields are empty
                            if not doc_id or not title or not similarity_str:
                                continue

                            similarity = float(similarity_str)

                            # Parse embedding from PostgreSQL vector format [0.1,0.2,...]
                            embedding = None
                            if embedding_str and embedding_str.startswith('[') and embedding_str.endswith(']'):
                                try:
                                    embedding = [float(x) for x in embedding_str[1:-1].split(',')]
                                except:
                                    pass

                            documents.append({
                                'id': doc_id,
                                'title': title,
                                'category': category,
                                'mode': mode_val,
                                'summary': summary,
                                'content': content,
                                'embedding': embedding,
                                'similarity': similarity,
                                'created_at': created_at,
                                'updated_at': updated_at
                            })
                        except (ValueError, IndexError) as e:
                            # Skip malformed lines
                            continue

            return documents

        except Exception as e:
            print(f"  ❌ Error searching similar documents: {e}")
            import traceback
            traceback.print_exc()
            return []

    def search_similar_sections(
        self,
        query_embedding: List[float],
        mode: str = None,
        limit: int = 10,
        min_similarity: float = 0.0
    ) -> List[Dict]:
        """
        Search for similar sections using PostgreSQL vector similarity

        Args:
            query_embedding: Query embedding vector (768 dimensions)
            mode: Optional filter by document mode ('paragraph' or 'full-doc')
            limit: Maximum number of results to return (default: 10)
            min_similarity: Minimum similarity score (0-1, default: 0.0)

        Returns:
            List of dicts with section info, parent document info, and similarity scores
        """
        try:
            # Build mode filter
            mode_filter = ""
            if mode:
                mode_filter = f"AND d.mode = '{mode}'"

            # Convert embedding to PostgreSQL vector format
            query_vec = self._quote_vector(query_embedding)

            sql = f"""
            SELECT
                s.id,
                s.document_id,
                s.section_index,
                s.header,
                s.content,
                s.token_count,
                s.keywords,
                s.topics,
                s.section_type,
                d.title as document_title,
                d.category as document_category,
                d.mode as document_mode,
                1 - (e.embedding <=> {query_vec}) AS similarity
            FROM semantic_sections s
            INNER JOIN embeddings e ON e.entity_type = 'section' AND e.entity_id = s.id
            INNER JOIN documents d ON s.document_id = d.id
            WHERE e.embedding IS NOT NULL
            {mode_filter}
            AND (1 - (e.embedding <=> {query_vec})) >= {min_similarity}
            ORDER BY e.embedding <=> {query_vec}
            LIMIT {limit};
            """

            result = subprocess.run(
                ["docker", "exec", self.container_name,
                 "psql", "-U", "postgres", "-d", self.database,
                 "-t", "-A", "-F", "|||", "-R", "\x1e", "-c", sql],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                print(f"  ❌ psql error: {result.stderr}")
                return []

            # Parse results
            sections = []
            if result.stdout and result.stdout.strip():
                records = result.stdout.strip().split('\x1e')

                for record in records:
                    if not record.strip():
                        continue

                    parts = record.split('|||')
                    if len(parts) >= 13:
                        try:
                            sections.append({
                                'id': parts[0].strip(),
                                'document_id': parts[1].strip(),
                                'section_index': int(parts[2].strip()),
                                'header': parts[3].strip(),
                                'content': parts[4].strip(),
                                'token_count': int(parts[5].strip()),
                                'keywords': parts[6].strip() if parts[6].strip() else None,
                                'topics': parts[7].strip() if parts[7].strip() else None,
                                'section_type': parts[8].strip(),
                                'document_title': parts[9].strip(),
                                'document_category': parts[10].strip(),
                                'document_mode': parts[11].strip(),
                                'similarity': float(parts[12].strip())
                            })
                        except (ValueError, IndexError):
                            continue

            return sections

        except Exception as e:
            print(f"  ❌ Error searching similar sections: {e}")
            import traceback
            traceback.print_exc()
            return []

    def search_similar_propositions(
        self,
        query_embedding: List[float],
        mode: str = None,
        limit: int = 10,
        min_similarity: float = 0.0
    ) -> List[Dict]:
        """
        Search for similar propositions using PostgreSQL vector similarity

        Args:
            query_embedding: Query embedding vector (768 dimensions)
            mode: Optional filter by document mode ('paragraph' or 'full-doc')
            limit: Maximum number of results to return (default: 10)
            min_similarity: Minimum similarity score (0-1, default: 0.0)

        Returns:
            List of dicts with proposition info, parent section/document info, and similarity scores
        """
        try:
            # Build mode filter
            mode_filter = ""
            if mode:
                mode_filter = f"AND d.mode = '{mode}'"

            # Convert embedding to PostgreSQL vector format
            query_vec = self._quote_vector(query_embedding)

            sql = f"""
            SELECT
                p.id,
                p.section_id,
                p.proposition_index,
                p.content,
                p.token_count,
                p.proposition_type,
                p.entities,
                p.keywords,
                s.document_id,
                s.section_index,
                s.header as section_header,
                d.title as document_title,
                d.category as document_category,
                d.mode as document_mode,
                1 - (e.embedding <=> {query_vec}) AS similarity
            FROM semantic_propositions p
            INNER JOIN embeddings e ON e.entity_type = 'proposition' AND e.entity_id = p.id
            INNER JOIN semantic_sections s ON p.section_id = s.id
            INNER JOIN documents d ON s.document_id = d.id
            WHERE e.embedding IS NOT NULL
            {mode_filter}
            AND (1 - (e.embedding <=> {query_vec})) >= {min_similarity}
            ORDER BY e.embedding <=> {query_vec}
            LIMIT {limit};
            """

            result = subprocess.run(
                ["docker", "exec", self.container_name,
                 "psql", "-U", "postgres", "-d", self.database,
                 "-t", "-A", "-F", "|||", "-R", "\x1e", "-c", sql],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                print(f"  ❌ psql error: {result.stderr}")
                return []

            # Parse results
            propositions = []
            if result.stdout and result.stdout.strip():
                records = result.stdout.strip().split('\x1e')

                for record in records:
                    if not record.strip():
                        continue

                    parts = record.split('|||')
                    if len(parts) >= 15:
                        try:
                            propositions.append({
                                'id': parts[0].strip(),
                                'section_id': parts[1].strip(),
                                'proposition_index': int(parts[2].strip()),
                                'content': parts[3].strip(),
                                'token_count': int(parts[4].strip()),
                                'proposition_type': parts[5].strip(),
                                'entities': parts[6].strip() if parts[6].strip() else None,
                                'keywords': parts[7].strip() if parts[7].strip() else None,
                                'document_id': parts[8].strip(),
                                'section_index': int(parts[9].strip()),
                                'section_header': parts[10].strip(),
                                'document_title': parts[11].strip(),
                                'document_category': parts[12].strip(),
                                'document_mode': parts[13].strip(),
                                'similarity': float(parts[14].strip())
                            })
                        except (ValueError, IndexError):
                            continue

            return propositions

        except Exception as e:
            print(f"  ❌ Error searching similar propositions: {e}")
            import traceback
            traceback.print_exc()
            return []

    def insert_documents_batch(self, documents: List[Dict]) -> Dict:
        """
        Insert multiple documents in batch

        Args:
            documents: List of document dicts

        Returns:
            Results dict with success/fail counts
        """
        print(f"\n{'='*80}")
        print(f"💾 BATCH DATABASE INSERTION")
        print(f"{'='*80}")
        print(f"Documents to insert: {len(documents)}")

        success_count = 0
        fail_count = 0
        failed_docs = []

        for i, doc in enumerate(documents, 1):
            print(f"\n[{i}/{len(documents)}] Inserting: {doc['title']}")
            if self.insert_document(doc):
                success_count += 1
            else:
                fail_count += 1
                failed_docs.append(doc['title'])

        # Print summary
        print(f"\n{'='*80}")
        print(f"📊 INSERTION SUMMARY")
        print(f"{'='*80}")
        print(f"\n✅ Success: {success_count}/{len(documents)}")
        print(f"❌ Failed: {fail_count}/{len(documents)}")

        if failed_docs:
            print(f"\nFailed documents:")
            for title in failed_docs:
                print(f"   • {title}")

        print(f"\n{'='*80}")

        return {
            "success_count": success_count,
            "fail_count": fail_count,
            "failed_docs": failed_docs,
            "total": len(documents)
        }

    def get_document_stats(self) -> Dict:
        """Get database statistics"""
        try:
            # Use simple docker exec for queries
            result = subprocess.run(
                ["docker", "exec", self.container_name,
                 "psql", "-U", self.user, "-d", self.database,
                 "-t", "-c", "SELECT COUNT(*) FROM documents;"],
                capture_output=True,
                text=True,
                check=True
            )
            doc_count = int(result.stdout.strip())

            result = subprocess.run(
                ["docker", "exec", self.container_name,
                 "psql", "-U", self.user, "-d", self.database,
                 "-t", "-c", "SELECT COUNT(*) FROM semantic_sections;"],
                capture_output=True,
                text=True,
                check=True
            )
            section_count = int(result.stdout.strip())

            result = subprocess.run(
                ["docker", "exec", self.container_name,
                 "psql", "-U", self.user, "-d", self.database,
                 "-t", "-c", "SELECT COUNT(*) FROM semantic_propositions;"],
                capture_output=True,
                text=True,
                check=True
            )
            prop_count = int(result.stdout.strip())

            result = subprocess.run(
                ["docker", "exec", self.container_name,
                 "psql", "-U", self.user, "-d", self.database,
                 "-t", "-c", "SELECT COUNT(*) FROM embeddings;"],
                capture_output=True,
                text=True,
                check=True
            )
            emb_count = int(result.stdout.strip())

            return {
                "documents": doc_count,
                "sections": section_count,
                "propositions": prop_count,
                "embeddings": emb_count
            }

        except Exception as e:
            print(f"  ❌ Error getting stats: {e}")
            return {}

    def print_stats(self):
        """Print database statistics"""
        stats = self.get_document_stats()

        print(f"\n{'='*80}")
        print(f"📊 DATABASE STATISTICS")
        print(f"{'='*80}")

        if not stats:
            print("  ⚠️  Unable to retrieve statistics")
            return

        print(f"\n📄 Documents: {stats['documents']}")
        print(f"📑 Sections: {stats['sections']}")
        print(f"💬 Propositions: {stats['propositions']}")
        print(f"🔢 Embeddings: {stats['embeddings']}")

        print(f"\n{'='*80}")


# Convenience function
def create_database(container_name: str = None, database: str = None) -> ChunkedDocumentDatabase:
    """Create and return database instance"""
    return ChunkedDocumentDatabase(container_name=container_name, database=database)
