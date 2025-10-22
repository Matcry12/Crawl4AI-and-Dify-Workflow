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
        self.container_name = container_name or os.getenv('POSTGRES_CONTAINER', 'docker-db-1')
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
            summary_embedding = json.dumps(chunks['summary_embedding'])
            sql_parts.append(f"""
INSERT INTO embeddings (entity_type, entity_id, embedding)
VALUES ('document_summary', {self._quote(doc_id)}, {self._quote(summary_embedding)}::jsonb)
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
                section_embedding = json.dumps(section['embedding'])
                sql_parts.append(f"""
INSERT INTO embeddings (entity_type, entity_id, embedding)
VALUES ('section', {self._quote(section_id)}, {self._quote(section_embedding)}::jsonb)
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
                    prop_embedding = json.dumps(prop['embedding'])
                    sql_parts.append(f"""
INSERT INTO embeddings (entity_type, entity_id, embedding)
VALUES ('proposition', {self._quote(prop_id)}, {self._quote(prop_embedding)}::jsonb)
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
