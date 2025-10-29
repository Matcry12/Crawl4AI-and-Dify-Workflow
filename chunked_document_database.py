#!/usr/bin/env python3
"""
Simple Document Database - Simplified 3-Table Schema

Works with the new simplified schema:
- documents (with keywords[], source_urls[])
- chunks (quality chunks for search)
- merge_history (tracking merges)

Supports:
- Parent Document Retrieval (search chunks, return documents)
- Atomic document+chunks updates
- Vector similarity search with pgvector
"""

import os
import json
from typing import List, Dict, Optional
from datetime import datetime


class SimpleDocumentDatabase:
    """
    Database interface for simplified RAG architecture

    Schema:
    - documents: Full documents (what LLM receives)
    - chunks: Quality chunks (for precise search)
    - merge_history: Merge tracking
    """

    def __init__(
        self,
        container_name: str = None,
        database: str = None,
        user: str = "postgres",
        password: str = "postgres",
        host: str = "localhost",
        port: int = 5432
    ):
        """
        Initialize database connection

        Args:
            container_name: Docker container name (will use docker exec)
            database: Database name
            user: Database user
            password: Database password
            host: Database host
            port: Database port
        """
        self.container_name = container_name or os.getenv('POSTGRES_CONTAINER', 'postgres-crawl4ai')
        self.database = database or os.getenv('POSTGRES_DATABASE', 'crawl4ai')
        self.user = user
        self.password = password
        self.host = host
        self.port = port

        # Use docker exec for local container
        self.use_docker = True

        print("✅ Simple document database initialized")
        print(f"   Container: {self.container_name}")
        print(f"   Database: {self.database}")
        print(f"   Schema: Simplified (documents + chunks + merge_history)")

    def _execute_query(self, query: str, params: tuple = None, fetch: bool = True):
        """Execute SQL query via docker exec"""
        import subprocess

        # Escape single quotes in query
        query_escaped = query.replace("'", "''")

        if params:
            # Simple parameter substitution for arrays and values
            for param in params:
                if isinstance(param, list):
                    # Convert Python list to PostgreSQL array
                    if not param:  # Empty array needs explicit type
                        param_str = "ARRAY[]::TEXT[]"
                    else:
                        param_str = "ARRAY[" + ",".join(f"'{str(p)}'" for p in param) + "]"
                    query_escaped = query_escaped.replace('%s', param_str, 1)
                elif param is None:
                    query_escaped = query_escaped.replace('%s', 'NULL', 1)
                else:
                    # Escape and quote string parameters
                    param_str = str(param).replace("'", "''")
                    query_escaped = query_escaped.replace('%s', f"'{param_str}'", 1)

        # Build psql command (pass query via stdin to avoid command-line length limits)
        cmd = [
            'docker', 'exec', '-i', self.container_name,
            'psql', '-U', self.user, '-d', self.database,
            '-t',  # Tuples only
            '-A',  # Unaligned output
            '-F', '|'  # Field separator
        ]

        try:
            result = subprocess.run(
                cmd,
                input=query_escaped,  # Pass query via stdin instead of -c
                capture_output=True,
                text=True,
                check=True
            )

            if fetch and result.stdout:
                # Parse results
                lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                return lines

            return []

        except subprocess.CalledProcessError as e:
            print(f"  ❌ Query failed: {e.stderr}")
            raise

    def insert_document(self, document: Dict) -> bool:
        """
        Insert document with chunks

        Args:
            document: Document dict with:
                - id, title, content, summary, category
                - keywords (list), source_urls (list)
                - embedding (list/vector)
                - chunks (list of chunk dicts with embeddings)

        Returns:
            Success boolean
        """
        try:
            # Insert document
            doc_query = """
                INSERT INTO documents (
                    id, title, content, summary, category,
                    keywords, source_urls, embedding,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector(768), NOW(), NOW())
            """

            self._execute_query(
                doc_query,
                (
                    document['id'],
                    document['title'],
                    document['content'],
                    document.get('summary', ''),
                    document.get('category', 'general'),
                    document.get('keywords', []),
                    document.get('source_urls', []),
                    json.dumps(document['embedding'])
                ),
                fetch=False
            )

            # Insert chunks
            chunks = document.get('chunks', [])
            for chunk in chunks:
                chunk_query = """
                    INSERT INTO chunks (
                        id, document_id, content, chunk_index,
                        token_count, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s::vector(768))
                """

                chunk_id = chunk.get('id', f"{document['id']}_chunk_{chunk['chunk_index']}")

                self._execute_query(
                    chunk_query,
                    (
                        chunk_id,
                        document['id'],
                        chunk['content'],
                        chunk['chunk_index'],
                        chunk['token_count'],
                        json.dumps(chunk['embedding'])
                    ),
                    fetch=False
                )

            return True

        except Exception as e:
            print(f"  ❌ Error inserting document: {e}")
            return False

    def insert_documents_batch(self, documents: List[Dict]) -> Dict:
        """
        Insert multiple documents in batch

        Args:
            documents: List of document dicts

        Returns:
            Result dict with success_count, failed_docs
        """
        print(f"\n{'='*80}")
        print(f"💾 BATCH DATABASE INSERTION")
        print(f"{'='*80}")
        print(f"Documents to insert: {len(documents)}")

        success_count = 0
        failed_docs = []

        for i, doc in enumerate(documents, 1):
            print(f"\n[{i}/{len(documents)}] Inserting: {doc.get('title', 'Unknown')}")

            if self.insert_document(doc):
                success_count += 1
                print(f"  ✅ Inserted successfully")
            else:
                failed_docs.append(doc.get('id', f'doc_{i}'))
                print(f"  ❌ Failed")

        print(f"\n{'='*80}")
        print(f"📊 INSERTION SUMMARY")
        print(f"{'='*80}")
        print(f"\n✅ Success: {success_count}/{len(documents)}")

        if failed_docs:
            print(f"❌ Failed: {len(failed_docs)}/{len(documents)}")
            print(f"\nFailed documents:")
            for doc_id in failed_docs[:5]:
                print(f"   • {doc_id}")
            if len(failed_docs) > 5:
                print(f"   ... and {len(failed_docs) - 5} more")

        print(f"\n{'='*80}")

        return {
            'success_count': success_count,
            'total': len(documents),
            'failed_docs': failed_docs
        }

    def get_document_by_id(self, doc_id: str) -> Optional[Dict]:
        """
        Get document by ID with all chunks

        Args:
            doc_id: Document ID

        Returns:
            Document dict with chunks, or None
        """
        try:
            # Get document
            doc_query = """
                SELECT id, title, content, summary, category,
                       keywords, source_urls, created_at, updated_at
                FROM documents
                WHERE id = %s
            """

            results = self._execute_query(doc_query, (doc_id,))

            if not results:
                return None

            # Parse document row (handle pipes in content/summary)
            # Format: id|title|content|summary|category|keywords|source_urls|created_at|updated_at
            # Use rsplit to separate predictable end fields
            # NOTE: Content may contain newlines, so join all result lines back together
            row = '\n'.join(results)

            # Split from right to get last 4 predictable fields: keywords|source_urls|created_at|updated_at
            right_parts = row.rsplit('|', maxsplit=4)

            if len(right_parts) < 5:
                print(f"  ⚠️  Malformed document row")
                return None

            # Now split the left part (id|title|content|summary|category) with maxsplit=4
            left_parts = right_parts[0].split('|', maxsplit=4)

            if len(left_parts) < 5:
                print(f"  ⚠️  Malformed document row (left fields)")
                return None

            document = {
                'id': left_parts[0],
                'title': left_parts[1],
                'content': left_parts[2],
                'summary': left_parts[3],
                'category': left_parts[4],
                'keywords': self._parse_array(right_parts[1]) if right_parts[1] != '' else [],
                'source_urls': self._parse_array(right_parts[2]) if right_parts[2] != '' else [],
                'created_at': right_parts[3],
                'updated_at': right_parts[4]
            }

            # Get chunks
            chunk_query = """
                SELECT id, content, chunk_index, token_count
                FROM chunks
                WHERE document_id = %s
                ORDER BY chunk_index
            """

            chunk_results = self._execute_query(chunk_query, (doc_id,))

            chunks = []
            # Group chunk result lines that belong to the same chunk
            # Each chunk starts when we see a new chunk_index value at the end
            current_chunk_lines = []
            for line in chunk_results:
                # Check if this line ends with a chunk_index pattern (e.g., "|0|123")
                # Split from right to see if we have the pattern
                test_parts = line.rsplit('|', maxsplit=2)
                if len(test_parts) == 3 and test_parts[1].isdigit() and test_parts[2].isdigit():
                    # This is the last line of a chunk (or a single-line chunk)
                    current_chunk_lines.append(line)
                    chunk_row = '\n'.join(current_chunk_lines)

                    # Parse chunk row (content may contain pipes and newlines)
                    # Format: id|content|chunk_index|token_count
                    # Split from right to get predictable last 2 fields
                    right_parts = chunk_row.rsplit('|', maxsplit=2)

                    if len(right_parts) >= 3:
                        # Split left part to get id|content
                        left_parts = right_parts[0].split('|', maxsplit=1)

                        if len(left_parts) >= 2:
                            chunks.append({
                                'id': left_parts[0],
                                'content': left_parts[1],
                                'chunk_index': int(right_parts[1]),
                                'token_count': int(right_parts[2])
                            })

                    # Reset for next chunk
                    current_chunk_lines = []
                else:
                    # This line is part of multi-line content, accumulate it
                    current_chunk_lines.append(line)

            document['chunks'] = chunks

            return document

        except Exception as e:
            print(f"  ❌ Error getting document '{doc_id}': {e}")
            import traceback
            traceback.print_exc()
            return None

    def search_parent_documents(
        self,
        query_embedding: list,
        top_k: int = 3,
        similarity_threshold: float = 0.5
    ) -> List[Dict]:
        """
        Parent Document Retrieval: Search chunks, return full documents

        Args:
            query_embedding: Query embedding vector
            top_k: Number of documents to return
            similarity_threshold: Minimum similarity score

        Returns:
            List of documents with scores and matching info
        """
        try:
            # Use the database function we created in schema
            # Use parameterized query to avoid quoting issues
            import json
            vector_json = json.dumps(query_embedding)

            query = f"""
                SELECT * FROM search_parent_documents(
                    %s::vector(768),
                    {similarity_threshold},
                    {top_k}
                )
            """

            results = self._execute_query(query, (vector_json,))

            # FIX: Group lines that belong to the same document
            # Each document record has 8 fields separated by 7 pipes: id|title|content|summary|keywords|source_urls|score|count
            # When content/summary have newlines, they get split across multiple result lines
            # Strategy: Detect document boundaries by counting pipes from the right

            document_records = []
            current_record_lines = []

            for line in results:
                # Count pipes from the right to detect if this completes a record
                # A complete record has at least 7 pipes (8 fields)
                pipe_count = line.count('|')

                # Check if this line could be the end of a record by splitting from right
                right_parts = line.rsplit('|', maxsplit=4)

                # If we can split into 5 parts from right, this might be the last line of a record
                # The last 4 fields after document ID should be: keywords|source_urls|score|count
                # These are predictable: keywords and source_urls are {...}, score is float, count is int
                if len(right_parts) == 5:
                    # Check if the last part looks like an integer (matching_chunk_count)
                    try:
                        int(right_parts[4])
                        # Check if second-to-last looks like a float (score)
                        float(right_parts[3])
                        # This looks like the end of a record
                        current_record_lines.append(line)
                        # Join all accumulated lines for this record
                        full_record = '\n'.join(current_record_lines)
                        document_records.append(full_record)
                        current_record_lines = []
                        continue
                    except (ValueError, IndexError):
                        pass

                # Not the end of a record, accumulate this line
                current_record_lines.append(line)

            # Handle any remaining lines (shouldn't happen with valid data)
            if current_record_lines:
                full_record = '\n'.join(current_record_lines)
                document_records.append(full_record)

            documents = []
            for row in document_records:
                # Parse carefully since content and summary may contain pipes and newlines
                # Format: id|title|content|summary|keywords|source_urls|score|count
                # Strategy: rsplit from right to get predictable fields first

                # Split from right to get last 4 predictable fields: keywords|source_urls|score|count
                right_parts = row.rsplit('|', maxsplit=4)

                if len(right_parts) < 5:
                    print(f"  ⚠️  Skipping malformed row (expected at least 5 parts)")
                    continue

                # Now split the left part (id|title|content|summary) with maxsplit=3
                left_parts = right_parts[0].split('|', maxsplit=3)

                if len(left_parts) < 4:
                    print(f"  ⚠️  Skipping malformed row (expected 4 left fields, got {len(left_parts)})")
                    continue

                doc = {
                    'id': left_parts[0],
                    'title': left_parts[1],
                    'content': left_parts[2],
                    'summary': left_parts[3],
                    'keywords': self._parse_array(right_parts[1]) if right_parts[1] != '' else [],
                    'source_urls': self._parse_array(right_parts[2]) if right_parts[2] != '' else [],
                    'score': float(right_parts[3]) if right_parts[3] else 0.0,
                    'matching_chunks': int(right_parts[4]) if right_parts[4] else 0
                }

                # Get all chunks for this document
                chunk_query = """
                    SELECT id, content, chunk_index, token_count
                    FROM chunks
                    WHERE document_id = %s
                    ORDER BY chunk_index
                """

                chunk_results = self._execute_query(chunk_query, (doc['id'],))

                # FIX: Handle chunks with newlines in content (same as get_document_by_id fix)
                chunks = []
                current_chunk_lines = []
                for line in chunk_results:
                    # Check if this line ends with a chunk_index pattern (e.g., "|0|123")
                    # Split from right to see if we have the pattern
                    test_parts = line.rsplit('|', maxsplit=2)
                    if len(test_parts) == 3 and test_parts[1].isdigit() and test_parts[2].isdigit():
                        # This is the last line of a chunk (or a single-line chunk)
                        current_chunk_lines.append(line)
                        chunk_row = '\n'.join(current_chunk_lines)

                        # Parse chunk row (content may contain pipes and newlines)
                        # Format: id|content|chunk_index|token_count
                        # Split from right to get predictable last 2 fields
                        right_parts = chunk_row.rsplit('|', maxsplit=2)

                        if len(right_parts) >= 3:
                            # Split left part to get id|content
                            left_parts = right_parts[0].split('|', maxsplit=1)

                            if len(left_parts) >= 2:
                                chunks.append({
                                    'id': left_parts[0],
                                    'content': left_parts[1],
                                    'chunk_index': int(right_parts[1]),
                                    'token_count': int(right_parts[2])
                                })

                        # Reset for next chunk
                        current_chunk_lines = []
                    else:
                        # This line is part of multi-line content, accumulate it
                        current_chunk_lines.append(line)

                doc['chunks'] = chunks
                documents.append(doc)

            return documents

        except Exception as e:
            print(f"  ❌ Error searching documents: {e}")
            import traceback
            traceback.print_exc()
            return []

    def update_document_with_chunks(self, document: Dict) -> bool:
        """
        Update document and replace all chunks (atomic)

        Critical for merge: ensures chunks always match document content

        Args:
            document: Updated document with new chunks

        Returns:
            Success boolean
        """
        try:
            # Start transaction
            self._execute_query("BEGIN", fetch=False)

            # Update document
            update_query = """
                UPDATE documents SET
                    content = %s,
                    summary = %s,
                    keywords = %s,
                    source_urls = %s,
                    updated_at = NOW(),
                    embedding = %s::vector(768)
                WHERE id = %s
            """

            self._execute_query(
                update_query,
                (
                    document['content'],
                    document.get('summary', ''),
                    document.get('keywords', []),
                    document.get('source_urls', []),
                    json.dumps(document['embedding']),
                    document['id']
                ),
                fetch=False
            )

            # Delete old chunks
            delete_query = "DELETE FROM chunks WHERE document_id = %s"
            self._execute_query(delete_query, (document['id'],), fetch=False)

            # Insert new chunks
            chunks = document.get('chunks', [])
            for chunk in chunks:
                chunk_query = """
                    INSERT INTO chunks (
                        id, document_id, content, chunk_index,
                        token_count, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s::vector(768))
                """

                chunk_id = chunk.get('id', f"{document['id']}_chunk_{chunk['chunk_index']}")

                self._execute_query(
                    chunk_query,
                    (
                        chunk_id,
                        document['id'],
                        chunk['content'],
                        chunk['chunk_index'],
                        chunk['token_count'],
                        json.dumps(chunk['embedding'])
                    ),
                    fetch=False
                )

            # Record merge if present
            if 'merge_history' in document:
                merge_query = """
                    INSERT INTO merge_history (
                        target_doc_id, source_topic_title,
                        merge_strategy, changes_made
                    ) VALUES (%s, %s, %s, %s)
                """

                self._execute_query(
                    merge_query,
                    (
                        document['id'],
                        document['merge_history'].get('source_topic_title', ''),
                        document['merge_history'].get('merge_strategy', ''),
                        document['merge_history'].get('changes_made', '')
                    ),
                    fetch=False
                )

            # Commit transaction
            self._execute_query("COMMIT", fetch=False)

            return True

        except Exception as e:
            # Rollback on error
            self._execute_query("ROLLBACK", fetch=False)
            print(f"  ❌ Error updating document: {e}")
            return False

    def get_all_documents_with_embeddings(self) -> List[Dict]:
        """
        Get all documents with embeddings (for merge decisions)

        Returns:
            List of documents with id, title, summary, keywords, category, embedding, chunk_count, content_length
        """
        try:
            query = """
                SELECT
                    d.id,
                    d.title,
                    d.summary,
                    d.category,
                    d.keywords,
                    d.source_urls,
                    d.embedding,
                    LENGTH(d.content) as content_length,
                    COUNT(c.id) as chunk_count
                FROM documents d
                LEFT JOIN chunks c ON d.id = c.document_id
                GROUP BY d.id, d.title, d.summary, d.category, d.keywords, d.source_urls, d.embedding, d.content
                ORDER BY d.created_at DESC
            """

            results = self._execute_query(query)

            # FIX: Group lines that belong to the same document record
            # Format: id|title|summary|category|keywords|source_urls|embedding|content_length|chunk_count (9 fields)
            # Problem: summary can contain newlines, causing split across multiple array elements
            document_records = []
            current_record_lines = []

            for line in results:
                # Try to detect if this line ends a complete record
                # Strategy: A complete record has exactly 9 pipe-separated fields
                # Check from right: last 6 fields are category|keywords|source_urls|embedding|content_length|chunk_count
                right_parts = line.rsplit('|', maxsplit=6)

                if len(right_parts) == 7:
                    # This could be the end of a record
                    # Validation: keywords and source_urls should be arrays (start with '{')
                    # embedding should be array (start with '[')
                    # content_length and chunk_count should be numbers
                    keywords_field = right_parts[2]
                    urls_field = right_parts[3]
                    embedding_field = right_parts[4]
                    content_len_field = right_parts[5]
                    chunk_count_field = right_parts[6]

                    # If fields look correct, this is likely a complete record end
                    if ((keywords_field.startswith('{') or keywords_field == '') and
                        (urls_field.startswith('{') or urls_field == '') and
                        (embedding_field.startswith('[') or embedding_field == '') and
                        content_len_field.isdigit() and chunk_count_field.isdigit()):
                        # This is the end of a record
                        current_record_lines.append(line)
                        full_record = '\n'.join(current_record_lines)
                        document_records.append(full_record)
                        current_record_lines = []
                        continue

                # Otherwise, accumulate this line
                current_record_lines.append(line)

            # Handle any remaining lines
            if current_record_lines:
                full_record = '\n'.join(current_record_lines)
                document_records.append(full_record)

            documents = []
            for row in document_records:
                # Now parse the complete record
                # Split from right to preserve newlines in summary field
                right_parts = row.rsplit('|', maxsplit=6)

                if len(right_parts) >= 7:
                    # Split the left part to get id and title
                    left_parts = right_parts[0].split('|', maxsplit=2)

                    if len(left_parts) >= 3:
                        doc = {
                            'id': left_parts[0],
                            'title': left_parts[1],
                            'summary': left_parts[2],  # Can contain newlines
                            'category': right_parts[1],
                            'keywords': self._parse_array(right_parts[2]) if right_parts[2] != '' else [],
                            'source_urls': self._parse_array(right_parts[3]) if right_parts[3] != '' else [],
                            'embedding': self._parse_vector(right_parts[4]) if right_parts[4] and right_parts[4] != '' else None,
                            'content_length': int(right_parts[5]) if right_parts[5].isdigit() else 0,
                            'chunk_count': int(right_parts[6]) if right_parts[6].isdigit() else 0
                        }
                        documents.append(doc)

            return documents

        except Exception as e:
            print(f"  ❌ Error getting documents: {e}")
            return []

    def _parse_array(self, array_str: str) -> List[str]:
        """Parse PostgreSQL array string to Python list"""
        if not array_str or array_str == '{}':
            return []

        # Remove braces and split
        array_str = array_str.strip('{}')
        if not array_str:
            return []

        return [item.strip('"') for item in array_str.split(',')]

    def _parse_vector(self, vector_str: str) -> List[float]:
        """Parse PostgreSQL vector string to Python list of floats"""
        import json

        if not vector_str or vector_str == '':
            return None

        try:
            # Vector format: [0.1,0.2,0.3,...]
            return json.loads(vector_str)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"  ⚠️  Error parsing vector: {e}")
            return None

    def begin_transaction(self):
        """Begin database transaction"""
        self._execute_query("BEGIN", fetch=False)

    def commit_transaction(self):
        """Commit database transaction"""
        self._execute_query("COMMIT", fetch=False)

    def rollback_transaction(self):
        """Rollback database transaction"""
        self._execute_query("ROLLBACK", fetch=False)

    def get_stats(self) -> Dict:
        """Get database statistics"""
        try:
            query = "SELECT * FROM database_stats"
            results = self._execute_query(query)

            if results:
                parts = results[0].split('|')
                return {
                    'total_documents': int(parts[0]),
                    'total_chunks': int(parts[1]),
                    'total_merges': int(parts[2]),
                    'avg_chunks_per_doc': float(parts[3]) if parts[3] != '' else 0.0,
                    'avg_tokens_per_doc': float(parts[4]) if parts[4] != '' else 0.0
                }

            return {}

        except Exception as e:
            print(f"  ❌ Error getting stats: {e}")
            return {}


# Backwards compatibility: create alias
ChunkedDocumentDatabase = SimpleDocumentDatabase


if __name__ == "__main__":
    # Test database connection
    db = SimpleDocumentDatabase()

    print("\n📊 Database Statistics:")
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
