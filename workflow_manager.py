#!/usr/bin/env python3
"""
Workflow Manager

Orchestrates the complete crawling and topic extraction workflow.
Each step is a separate node that can be controlled and monitored.
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

# Database configuration
USE_POSTGRESQL = os.getenv('USE_POSTGRESQL', 'true').lower() == 'true'
POSTGRES_CONTAINER = os.getenv('POSTGRES_CONTAINER', 'postgres-crawl4ai')
POSTGRES_DATABASE = os.getenv('POSTGRES_DATABASE', 'crawl4ai')

if USE_POSTGRESQL:
    print(f"🐘 PostgreSQL enabled (container: {POSTGRES_CONTAINER}, database: {POSTGRES_DATABASE})")
else:
    print("📁 SQLite enabled")


class NodeStatus(Enum):
    """Status of a workflow node"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowNode:
    """Base class for workflow nodes"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.status = NodeStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.error = None
        self.result = None

    def start(self):
        """Mark node as running"""
        self.status = NodeStatus.RUNNING
        self.start_time = datetime.now()
        print(f"\n{'='*80}")
        print(f"🔵 [{self.name}] {self.description}")
        print(f"{'='*80}")

    def complete(self, result=None):
        """Mark node as completed"""
        self.status = NodeStatus.COMPLETED
        self.end_time = datetime.now()
        self.result = result
        duration = (self.end_time - self.start_time).total_seconds()
        print(f"\n✅ [{self.name}] Completed in {duration:.2f}s")

    def fail(self, error: str):
        """Mark node as failed"""
        self.status = NodeStatus.FAILED
        self.end_time = datetime.now()
        self.error = error
        print(f"\n❌ [{self.name}] Failed: {error}")

    def skip(self, reason: str):
        """Mark node as skipped"""
        self.status = NodeStatus.SKIPPED
        self.error = reason
        print(f"\n⏭️  [{self.name}] Skipped: {reason}")


class CrawlNode(WorkflowNode):
    """Node for crawling websites"""

    def __init__(self):
        super().__init__(
            name="Crawl",
            description="Crawl website using BFS algorithm"
        )

    async def execute(
        self,
        start_url: str,
        max_pages: int,
        same_domain_only: bool,
        output_dir: str
    ) -> Dict:
        """Execute crawling"""
        from bfs_crawler import BFSCrawler

        self.start()

        try:
            # Create crawler (without auto-extraction)
            crawler = BFSCrawler(
                start_url=start_url,
                max_pages=max_pages,
                same_domain_only=same_domain_only,
                output_dir=output_dir,
                extract_topics=False  # Managed by workflow
            )

            # Run crawl
            await crawler.crawl_bfs()

            # Save report
            crawler.save_report()

            # Validate that at least one page was successfully crawled
            pages_crawled = len(crawler.successful)
            pages_failed = len(crawler.failed)

            if pages_crawled == 0:
                # No pages successfully crawled
                error_msg = f"Crawl failed: No pages successfully crawled (0/{pages_crawled + pages_failed} succeeded)"
                if pages_failed > 0:
                    error_msg += f". All {pages_failed} pages failed."
                else:
                    error_msg += ". No pages were found or accessible."

                print(f"\n❌ {error_msg}")
                print(f"   Start URL: {start_url}")
                print(f"   Check if URL is accessible and returns valid HTML")

                self.fail(error_msg)
                raise ValueError(error_msg)

            # Prepare result
            result = {
                'crawler': crawler,
                'pages_crawled': pages_crawled,
                'pages_failed': pages_failed,
                'links_discovered': len(crawler.to_visit),
                'output_dir': crawler.output_dir
            }

            self.complete(result)
            return result

        except Exception as e:
            self.fail(str(e))
            raise


class ExtractTopicsNode(WorkflowNode):
    """Node for extracting topics"""

    def __init__(self):
        super().__init__(
            name="Extract Topics",
            description="Extract topics from crawled content using LLM"
        )

    async def execute(self, crawl_result: Dict) -> Dict:
        """Execute topic extraction"""
        from extract_topics import TopicExtractor

        self.start()

        try:
            # Validate crawl_result parameter
            if not crawl_result:
                self.skip("No crawl result provided")
                return None

            if not crawl_result.get('output_dir'):
                self.skip("Crawl result missing output_dir")
                return None

            # Check if any pages were crawled
            pages_crawled = crawl_result.get('pages_crawled', 0)
            if pages_crawled == 0:
                self.skip(f"No pages were successfully crawled (cannot extract topics from empty data)")
                return None

            # Check GEMINI_API_KEY
            if not os.getenv('GEMINI_API_KEY'):
                self.skip("GEMINI_API_KEY not set")
                return None

            # Initialize extractor
            print("✅ Topic extractor initialized")
            extractor = TopicExtractor()

            # Extract topics
            output_dir = str(crawl_result['output_dir'])
            all_topics = await extractor.extract_from_crawled_files(output_dir)

            if not all_topics:
                self.skip("No topics extracted from crawled content")
                return None

            # Save report
            extractor.save_report(all_topics, f"{output_dir}/topics_report.txt")

            # Prepare result
            result = {
                'all_topics': all_topics,
                'urls_processed': len(all_topics),
                'total_topics': sum(len(topics) for topics in all_topics.values())
            }

            self.complete(result)
            return result

        except Exception as e:
            self.fail(str(e))
            raise


class EmbeddingSearchNode(WorkflowNode):
    """Node for embedding-based document search"""

    def __init__(self):
        super().__init__(
            name="Embedding Search",
            description="Search for similar documents using embeddings"
        )

    async def execute(self, extract_result: Dict, existing_documents: List[Dict] = None, mode_filter: str = None) -> Dict:
        """
        Execute embedding search

        Args:
            extract_result: Result from topic extraction
            existing_documents: List of existing documents to compare against
            mode_filter: Optional mode filter ("paragraph" or "full-doc")
                        If specified, only compare with documents of this mode
        """
        from embedding_search import EmbeddingSearcher

        self.start()

        try:
            # Check GEMINI_API_KEY
            if not os.getenv('GEMINI_API_KEY'):
                self.skip("GEMINI_API_KEY not set")
                return None

            # Check if extraction succeeded
            if not extract_result or not extract_result.get('all_topics'):
                self.skip("No topics to process from extraction")
                return None

            # Initialize database for PostgreSQL vector search (if enabled)
            db = None
            if USE_POSTGRESQL:
                from chunked_document_database import ChunkedDocumentDatabase
                db = ChunkedDocumentDatabase(
                    container_name=POSTGRES_CONTAINER,
                    database=POSTGRES_DATABASE
                )

            # Initialize searcher with database for PostgreSQL vector search
            searcher = EmbeddingSearcher(use_postgres_search=USE_POSTGRESQL, db=db)

            # Get all topics from extraction result
            all_topics = []
            for topics in extract_result['all_topics'].values():
                all_topics.extend(topics)

            # Validate that we have topics to process
            if len(all_topics) == 0:
                self.skip("No topics to process (empty list after flattening)")
                return None

            print(f"📋 Processing {len(all_topics)} topics")
            if mode_filter:
                print(f"   Mode Filter: {mode_filter}")

            # Use empty list if no existing documents provided
            if existing_documents is None:
                existing_documents = []
                print("ℹ️  No existing documents provided - all topics will be marked for creation")

            # Process topics with mode filter
            results = searcher.batch_process_topics(all_topics, existing_documents, mode_filter=mode_filter)

            # Prepare result summary
            result = {
                'results': results,
                'total_topics': len(all_topics),
                'merge_count': len(results['merge']),
                'create_count': len(results['create']),
                'verify_count': len(results['verify']),
                'llm_calls_saved': len(results['merge']) + len(results['create']),
                'mode_filter': mode_filter
            }

            self.complete(result)
            return result

        except Exception as e:
            self.fail(str(e))
            raise


class LLMVerificationNode(WorkflowNode):
    """Node for LLM verification of uncertain topics"""

    def __init__(self):
        super().__init__(
            name="LLM Verification",
            description="Verify uncertain topics using LLM to decide merge or create"
        )

    async def execute(self, embedding_result: Dict) -> Dict:
        """
        Execute LLM verification for topics with uncertain similarity

        Args:
            embedding_result: Result from embedding search node containing
                            topics in results['verify'] that need LLM judgment

        Returns:
            Updated embedding result with verified topics moved to merge/create
        """
        from llm_verifier import LLMVerifier

        self.start()

        try:
            # Check GEMINI_API_KEY
            if not os.getenv('GEMINI_API_KEY'):
                self.skip("GEMINI_API_KEY not set")
                return embedding_result  # Return unchanged

            # Check if there are topics to verify
            results = embedding_result.get('results', {})
            verify_items = results.get('verify', [])

            if not verify_items:
                self.skip("No topics require LLM verification")
                return embedding_result  # Return unchanged

            # Deduplicate verify items by topic ID (handles dual-mode duplicates)
            seen_ids = set()
            unique_verify_items = []
            for item in verify_items:
                topic = item.get('topic', {})
                # Use topic ID or title as unique identifier
                topic_id = topic.get('id') or topic.get('title', '')
                if topic_id and topic_id not in seen_ids:
                    seen_ids.add(topic_id)
                    unique_verify_items.append(item)

            duplicates_removed = len(verify_items) - len(unique_verify_items)
            if duplicates_removed > 0:
                print(f"   ℹ️  Removed {duplicates_removed} duplicate topics from verification queue")
                print(f"   Unique topics to verify: {len(unique_verify_items)}")

            if not unique_verify_items:
                self.skip("All verify topics were duplicates (already handled)")
                return embedding_result

            # Initialize verifier
            print(f"✅ LLM verifier initialized")
            verifier = LLMVerifier()

            # Get rate limit delay from environment
            rate_limit = float(os.getenv('RATE_LIMIT_DELAY', '1.0'))

            # Verify all uncertain topics (deduplicated)
            verified_results = verifier.batch_verify_topics(unique_verify_items, rate_limit_delay=rate_limit)

            # Update embedding result - move verified topics to merge/create
            embedding_result['results']['merge'].extend(verified_results['merge'])
            embedding_result['results']['create'].extend(verified_results['create'])
            embedding_result['results']['verify'] = []  # Clear verify list

            # Update counts
            embedding_result['merge_count'] += verified_results['merge_count']
            embedding_result['create_count'] += verified_results['create_count']
            embedding_result['verify_count'] = 0
            embedding_result['llm_verifications'] = verified_results['total_verified']

            # Prepare result summary
            result = {
                'total_verified': verified_results['total_verified'],
                'merged_after_llm': verified_results['merge_count'],
                'created_after_llm': verified_results['create_count'],
                'updated_embedding_result': embedding_result
            }

            self.complete(result)
            return embedding_result  # Return updated result

        except Exception as e:
            self.fail(str(e))
            # On failure, return unchanged result (topics stay in verify)
            return embedding_result


class DocumentCreatorNode(WorkflowNode):
    """Node for creating documents from topics"""

    def __init__(self):
        super().__init__(
            name="Document Creator",
            description="Create documents from topics in paragraph and full-doc modes"
        )

    async def execute(
        self,
        embedding_result: Dict,
        mode: str = "both"
    ) -> Dict:
        """
        Execute document creation

        Args:
            embedding_result: Result from embedding search node
            mode: "paragraph", "full-doc", or "both"

        Returns:
            Document creation results
        """
        from document_creator import DocumentCreator

        self.start()

        try:
            # Check GEMINI_API_KEY
            if not os.getenv('GEMINI_API_KEY'):
                self.skip("GEMINI_API_KEY not set")
                return None

            # Check if embedding search succeeded
            if not embedding_result or not embedding_result.get('results'):
                self.skip("No topics to create documents from")
                return None

            # Initialize creator
            print("✅ Document creator initialized")
            creator = DocumentCreator()

            # Get topics that need document creation
            results = embedding_result['results']

            # Collect all topics marked for creation
            create_topics = []
            for item in results['create']:
                create_topics.append(item['topic'])

            # NOTE: Verify topics should be handled by LLMVerificationNode first
            # If verification is skipped/disabled, we still create them as fallback
            verify_topics = results.get('verify', [])
            if verify_topics:
                print(f"   ⚠️  Warning: {len(verify_topics)} topics still in 'verify' state")
                print(f"   These should have been verified by LLM Verification node")
                print(f"   Creating them as new documents (fallback behavior)")
                for item in verify_topics:
                    create_topics.append(item['topic'])

            if not create_topics:
                self.skip("No topics require document creation")
                return None

            print(f"📋 Creating documents for {len(create_topics)} topics")
            print(f"   Mode: {mode.upper()}")

            # Create documents based on mode (chunking happens automatically!)
            if mode == "both":
                doc_results = creator.create_documents_both_modes(create_topics)
                all_documents = doc_results['paragraph_documents'] + doc_results['fulldoc_documents']
            elif mode == "paragraph":
                doc_results = creator.create_documents_batch(create_topics, mode="paragraph")
                all_documents = doc_results['documents']
            elif mode == "full-doc":
                doc_results = creator.create_documents_batch(create_topics, mode="full-doc")
                all_documents = doc_results['documents']
            else:
                raise ValueError(f"Invalid mode: {mode}")

            # Save to CHUNKED database (PostgreSQL with 3-level hierarchy)
            db_save_success = False
            db_result = None

            if USE_POSTGRESQL:
                from chunked_document_database import ChunkedDocumentDatabase

                print("\n💾 Saving documents with chunks to PostgreSQL...")
                try:
                    chunked_db = ChunkedDocumentDatabase()
                    db_result = chunked_db.insert_documents_batch(all_documents)

                    saved_count = db_result.get('success_count', 0)
                    total_count = db_result.get('total', 0)

                    print(f"   ✅ Saved: {saved_count}/{total_count} documents to chunked database")

                    if db_result.get('failed_docs'):
                        failed_docs = db_result['failed_docs']
                        print(f"   ⚠️  Failed: {', '.join(failed_docs[:5])}")
                        if len(failed_docs) > 5:
                            print(f"   ... and {len(failed_docs) - 5} more")

                    # Check if save was successful
                    if saved_count == 0:
                        # Total failure - no documents saved
                        error_msg = f"Database save failed: 0/{total_count} documents saved"
                        print(f"   ❌ {error_msg}")
                        self.fail(error_msg)
                        raise RuntimeError(error_msg)
                    elif saved_count < total_count:
                        # Partial success - some documents saved
                        print(f"   ⚠️  Partial save: {saved_count}/{total_count} documents saved")
                        print(f"   ℹ️  Continuing with warning (partial data loss)")
                        db_save_success = True  # Partial success
                    else:
                        # Complete success
                        db_save_success = True

                except Exception as e:
                    # Database save completely failed
                    print(f"   ❌ Chunked database save failed: {e}")
                    print(f"   ℹ️  Documents created in memory but NOT saved to database")
                    import traceback
                    traceback.print_exc()

                    # Check if this is a connection error or data error
                    error_str = str(e).lower()
                    if any(keyword in error_str for keyword in ['connection', 'could not connect', 'timeout', 'refused']):
                        error_msg = f"Database connection failed: {e}"
                    else:
                        error_msg = f"Database save failed: {e}"

                    # CRITICAL: Fail the node to prevent silent data loss
                    self.fail(error_msg)
                    raise RuntimeError(f"{error_msg} - No documents saved to database") from e
            else:
                # SQLite mode: Save to file only (old database schema incompatible with chunks)
                print("\n💾 Saving documents to files (SQLite not supported for chunked documents)...")
                print(f"   ℹ️  To enable chunked database storage, set USE_POSTGRESQL=true in .env")

                try:
                    # Save to files only
                    creator.save_documents(doc_results, output_dir="documents", save_to_db=False)
                    db_save_success = True  # File save is our "database" in SQLite mode
                except Exception as e:
                    print(f"   ❌ File save failed: {e}")
                    self.fail(f"File save failed: {e}")
                    raise

            # Prepare result
            result = {
                'mode': mode,
                'doc_results': doc_results,
                'total_topics': len(create_topics),
                'documents_created': doc_results.get('total_documents', doc_results.get('success_count', 0)),
                'failed_count': doc_results.get('fail_count', 0),
                'db_save_success': db_save_success,
                'db_saved_count': db_result.get('success_count', 0) if db_result else 0,
                'db_failed_count': len(db_result.get('failed_docs', [])) if db_result else 0
            }

            self.complete(result)
            return result

        except Exception as e:
            self.fail(str(e))
            raise


class DocumentMergerNode(WorkflowNode):
    """Node for merging topics with existing documents"""

    def __init__(self):
        super().__init__(
            name="Document Merger",
            description="Merge topics with existing documents in paragraph and full-doc modes"
        )

    async def execute(
        self,
        embedding_result: Dict,
        existing_documents_para: List[Dict] = None,
        existing_documents_full: List[Dict] = None,
        mode: str = "both"
    ) -> Dict:
        """
        Execute document merging

        Args:
            embedding_result: Result from embedding search node
            existing_documents_para: List of existing paragraph documents
            existing_documents_full: List of existing full documents
            mode: "paragraph", "full-doc", or "both"

        Returns:
            Document merge results
        """
        from document_merger import DocumentMerger

        self.start()

        try:
            # Check GEMINI_API_KEY
            if not os.getenv('GEMINI_API_KEY'):
                self.skip("GEMINI_API_KEY not set")
                return None

            # Check if embedding search succeeded
            if not embedding_result or not embedding_result.get('results'):
                self.skip("No embedding results to merge")
                return None

            # Initialize merger
            print("✅ Document merger initialized")
            merger = DocumentMerger()

            # Get topics that need merging
            results = embedding_result['results']

            # Collect merge topics
            merge_topics = []
            for item in results['merge']:
                merge_topics.append({
                    'topic': item['topic'],
                    'target_document': item['decision']['target_document']
                })

            if not merge_topics:
                self.skip("No topics require merging")
                return None

            print(f"📋 Merging {len(merge_topics)} topics with existing documents")
            print(f"   Mode: {mode.upper()}")

            # Prepare merge pairs based on mode
            if mode == "both":
                # Need both paragraph and full-doc versions of existing documents
                # Group merge topics by base document ID to avoid duplicates
                base_doc_map = {}
                for mt in merge_topics:
                    target_id = mt['target_document']['id']
                    base_id = self._get_base_document_id(target_id)

                    if base_id not in base_doc_map:
                        base_doc_map[base_id] = {
                            'topic': mt['topic'],
                            'base_id': base_id
                        }

                # Create merge pairs using base ID to find both versions
                merge_pairs = []
                for base_id, data in base_doc_map.items():
                    # Find both paragraph and full-doc versions using base ID
                    para_doc = self._find_document_by_base_id(base_id, existing_documents_para)
                    full_doc = self._find_document_by_base_id(base_id, existing_documents_full)

                    merge_pairs.append({
                        'topic': data['topic'],
                        'para_document': para_doc,
                        'fulldoc_document': full_doc
                    })

                merge_results = merger.merge_documents_both_modes(merge_pairs)

            elif mode == "paragraph":
                merge_pairs = []
                for mt in merge_topics:
                    para_doc = self._find_document(mt['target_document']['id'], existing_documents_para)
                    if para_doc:
                        merge_pairs.append({
                            'topic': mt['topic'],
                            'existing_document': para_doc
                        })

                merge_results = merger.merge_documents_batch(merge_pairs, mode="paragraph")

            elif mode == "full-doc":
                merge_pairs = []
                for mt in merge_topics:
                    full_doc = self._find_document(mt['target_document']['id'], existing_documents_full)
                    if full_doc:
                        merge_pairs.append({
                            'topic': mt['topic'],
                            'existing_document': full_doc
                        })

                merge_results = merger.merge_documents_batch(merge_pairs, mode="full-doc")
            else:
                raise ValueError(f"Invalid mode: {mode}")

            # Save merged documents (to files and update database)
            merger.save_merged_documents(merge_results, output_dir="merged_documents", save_to_db=True, db_path="documents.db")

            # Prepare result
            result = {
                'mode': mode,
                'merge_results': merge_results,
                'total_topics': len(merge_topics),
                'documents_merged': merge_results.get('total_merged', merge_results.get('success_count', 0)),
                'failed_count': merge_results.get('fail_count', 0)
            }

            self.complete(result)
            return result

        except Exception as e:
            self.fail(str(e))
            raise

    def _find_document(self, doc_id: str, documents: List[Dict]) -> Optional[Dict]:
        """Find document by ID in list"""
        if not documents:
            return None

        for doc in documents:
            if doc.get('id') == doc_id:
                return doc

        return None

    def _get_base_document_id(self, doc_id: str) -> str:
        """
        Extract base document ID without mode suffix

        E.g., 'eos_network_smart_contract_paragraph' -> 'eos_network_smart_contract'
              'eos_network_smart_contract_full-doc' -> 'eos_network_smart_contract'
        """
        if doc_id.endswith('_paragraph'):
            return doc_id[:-len('_paragraph')]
        elif doc_id.endswith('_full-doc'):
            return doc_id[:-len('_full-doc')]
        return doc_id

    def _find_document_by_base_id(self, base_id: str, documents: List[Dict]) -> Optional[Dict]:
        """Find document by base ID (matching without mode suffix)"""
        if not documents:
            return None

        for doc in documents:
            doc_base_id = self._get_base_document_id(doc.get('id', ''))
            if doc_base_id == base_id:
                return doc

        return None


class WorkflowManager:
    """
    Manages the complete workflow of crawling and topic extraction
    """

    def __init__(self):
        self.nodes: List[WorkflowNode] = []
        self.start_time = None
        self.end_time = None

    def add_node(self, node: WorkflowNode):
        """Add a node to the workflow"""
        self.nodes.append(node)

    def print_status(self):
        """Print current status of all nodes"""
        print(f"\n{'='*80}")
        print("📊 WORKFLOW STATUS")
        print(f"{'='*80}")

        for i, node in enumerate(self.nodes, 1):
            status_icon = {
                NodeStatus.PENDING: "⏸️ ",
                NodeStatus.RUNNING: "🔵",
                NodeStatus.COMPLETED: "✅",
                NodeStatus.FAILED: "❌",
                NodeStatus.SKIPPED: "⏭️ "
            }[node.status]

            print(f"{i}. {status_icon} [{node.name}] {node.status.value}")

            if node.status == NodeStatus.COMPLETED and node.result:
                if node.name == "Crawl":
                    print(f"   Pages: {node.result['pages_crawled']}, Links: {node.result['links_discovered']}")
                elif node.name == "Extract Topics":
                    print(f"   Topics: {node.result['total_topics']}, URLs: {node.result['urls_processed']}")
                elif node.name == "Embedding Search":
                    print(f"   Merge: {node.result['merge_count']}, Create: {node.result['create_count']}, Verify: {node.result['verify_count']}")
                    print(f"   LLM calls saved: {node.result['llm_calls_saved']}")
                elif node.name == "LLM Verification":
                    print(f"   Verified: {node.result['total_verified']}, Merge: {node.result['merged_after_llm']}, Create: {node.result['created_after_llm']}")
                elif node.name == "Document Creator":
                    print(f"   Mode: {node.result['mode']}, Documents: {node.result['documents_created']}")
                    if node.result.get('db_save_success'):
                        saved = node.result.get('db_saved_count', 0)
                        failed = node.result.get('db_failed_count', 0)
                        if failed > 0:
                            print(f"   Database: {saved} saved, {failed} failed (partial success)")
                        else:
                            print(f"   Database: {saved} saved successfully")
                    else:
                        print(f"   Database: Save failed (data loss)")
                    if node.result.get('failed_count', 0) > 0:
                        print(f"   Creation failed: {node.result['failed_count']}")
                elif node.name == "Document Merger":
                    print(f"   Mode: {node.result['mode']}, Documents: {node.result['documents_merged']}")
                    if node.result.get('failed_count', 0) > 0:
                        print(f"   Failed: {node.result['failed_count']}")

        print(f"{'='*80}")

    def print_summary(self):
        """Print final summary"""
        duration = (self.end_time - self.start_time).total_seconds()

        print(f"\n{'='*80}")
        print("✅ WORKFLOW COMPLETE!")
        print(f"{'='*80}")
        print(f"⏱️  Total time: {duration:.2f}s")
        print(f"\n📊 Nodes Summary:")

        for node in self.nodes:
            status_icon = {
                NodeStatus.COMPLETED: "✅",
                NodeStatus.FAILED: "❌",
                NodeStatus.SKIPPED: "⏭️ "
            }.get(node.status, "⏸️ ")

            print(f"   {status_icon} {node.name}: {node.status.value}")

        # Print results
        crawl_node = next((n for n in self.nodes if n.name == "Crawl"), None)
        extract_node = next((n for n in self.nodes if n.name == "Extract Topics"), None)
        embedding_node = next((n for n in self.nodes if n.name == "Embedding Search"), None)
        document_node = next((n for n in self.nodes if n.name == "Document Creator"), None)
        merger_node = next((n for n in self.nodes if n.name == "Document Merger"), None)

        if crawl_node and crawl_node.result:
            print(f"\n📁 Output:")
            print(f"   Directory: {crawl_node.result['output_dir']}/")
            print(f"   Crawl report: {crawl_node.result['output_dir']}/crawl_report.txt")

            if extract_node and extract_node.result:
                print(f"   Topics report: {crawl_node.result['output_dir']}/topics_report.txt")
                print(f"   Topics JSON: {crawl_node.result['output_dir']}/topics_report.json")

            if embedding_node and embedding_node.result:
                print(f"\n📊 Embedding Search Results:")
                print(f"   Total topics: {embedding_node.result['total_topics']}")
                print(f"   🔗 Merge: {embedding_node.result['merge_count']} (similarity > 0.85)")
                print(f"   ✨ Create: {embedding_node.result['create_count']} (similarity < 0.4)")
                print(f"   🤔 Verify: {embedding_node.result['verify_count']} (needs LLM)")
                print(f"   💰 LLM calls saved: {embedding_node.result['llm_calls_saved']}")

            if document_node and document_node.result:
                print(f"\n📚 Document Creation Results:")
                print(f"   Mode: {document_node.result['mode'].upper()}")
                print(f"   Topics processed: {document_node.result['total_topics']}")
                print(f"   Documents created: {document_node.result['documents_created']}")

                # Database save status
                if document_node.result.get('db_save_success'):
                    saved = document_node.result.get('db_saved_count', 0)
                    failed = document_node.result.get('db_failed_count', 0)
                    if failed > 0:
                        print(f"   ⚠️  Database: {saved}/{saved+failed} saved (partial success)")
                    else:
                        print(f"   ✅ Database: All {saved} documents saved successfully")
                else:
                    print(f"   ❌ Database: Save FAILED - documents NOT persisted")

                if document_node.result.get('failed_count', 0) > 0:
                    print(f"   Creation failed: {document_node.result['failed_count']}")
                print(f"   Output directory: documents/")

            if merger_node and merger_node.result:
                print(f"\n🔀 Document Merge Results:")
                print(f"   Mode: {merger_node.result['mode'].upper()}")
                print(f"   Topics processed: {merger_node.result['total_topics']}")
                print(f"   Documents merged: {merger_node.result['documents_merged']}")
                if merger_node.result.get('failed_count', 0) > 0:
                    print(f"   Failed: {merger_node.result['failed_count']}")
                print(f"   Output directory: merged_documents/")

        print(f"{'='*80}")

    async def run(
        self,
        start_url: str,
        max_pages: int = 50,
        same_domain_only: bool = True,
        output_dir: str = "bfs_crawled",
        extract_topics: bool = True,
        embedding_search: bool = True,
        existing_documents: List[Dict] = None,
        create_documents: bool = True,
        merge_documents: bool = True,
        document_mode: str = "both",
        existing_documents_para: List[Dict] = None,
        existing_documents_full: List[Dict] = None
    ):
        """
        Run the complete workflow

        Args:
            start_url: URL to start crawling from
            max_pages: Maximum pages to crawl
            same_domain_only: Only crawl same domain
            output_dir: Output directory
            extract_topics: Whether to extract topics
            embedding_search: Whether to run embedding search
            existing_documents: List of existing documents for similarity comparison
            create_documents: Whether to create documents from topics
            merge_documents: Whether to merge topics with existing documents
            document_mode: "paragraph", "full-doc", or "both"
            existing_documents_para: Existing paragraph documents for merging
            existing_documents_full: Existing full documents for merging
        """
        self.start_time = datetime.now()

        print(f"{'='*80}")
        print("🚀 WORKFLOW MANAGER")
        print(f"{'='*80}")
        print(f"Start URL: {start_url}")
        print(f"Max pages: {max_pages}")
        print(f"Same domain: {same_domain_only}")
        print(f"Output dir: {output_dir}")
        print(f"Extract topics: {extract_topics}")

        # Node 1: Crawl
        crawl_node = CrawlNode()
        self.add_node(crawl_node)

        crawl_result = await crawl_node.execute(
            start_url=start_url,
            max_pages=max_pages,
            same_domain_only=same_domain_only,
            output_dir=output_dir
        )

        # Validate crawl succeeded before continuing
        if not crawl_result or crawl_node.status == NodeStatus.FAILED:
            print("\n❌ Crawl failed - cannot continue workflow")
            self.end_time = datetime.now()
            self.print_summary()
            return

        # Print status after crawl
        self.print_status()

        # Node 2: Extract Topics (if enabled)
        extract_result = None
        if extract_topics:
            extract_node = ExtractTopicsNode()
            self.add_node(extract_node)

            extract_result = await extract_node.execute(crawl_result)

            # Print status after extraction
            self.print_status()

        # Node 3: Embedding Search (if enabled and topics were extracted)
        embedding_result = None
        if embedding_search and extract_result:
            # Load existing documents from database if not provided
            # NOTE: Only needed for Python fallback mode
            # PostgreSQL mode queries embeddings directly from database
            if existing_documents is None:
                if USE_POSTGRESQL:
                    # PostgreSQL mode: Skip loading embeddings (queried directly in database)
                    print(f"\n{'='*80}")
                    print("📚 PostgreSQL mode: Embeddings will be queried directly from database")
                    print("   ⚡ Skipping upfront loading (optimization)")
                    print(f"{'='*80}")
                    existing_documents = []  # Empty list, not used by PostgreSQL search
                else:
                    # Python fallback mode: Load embeddings for in-memory comparison
                    print(f"\n{'='*80}")
                    print("📚 Loading existing documents from database")
                    print(f"{'='*80}")

                    try:
                        from document_database import DocumentDatabase
                        db = DocumentDatabase(db_path="documents.db")
                        existing_documents = db.get_all_documents()

                        if existing_documents:
                            print(f"✅ Loaded {len(existing_documents)} existing documents")

                            # Show breakdown by mode
                            para_count = sum(1 for doc in existing_documents if doc.get('mode') == 'paragraph')
                            full_count = sum(1 for doc in existing_documents if doc.get('mode') == 'full-doc')
                            print(f"   Paragraph mode: {para_count}")
                            print(f"   Full-doc mode: {full_count}")
                        else:
                            print("ℹ️  No existing documents found in database")
                            existing_documents = []

                    except FileNotFoundError:
                        print("ℹ️  Database file not found - treating as first run")
                        existing_documents = []
                    except Exception as e:
                        print(f"⚠️  Could not load existing documents: {e}")
                        existing_documents = []

                    print(f"{'='*80}")

            embedding_node = EmbeddingSearchNode()
            self.add_node(embedding_node)

            # IMPORTANT: When document_mode="both", we need to run embedding search TWICE
            # - Once for paragraph mode (compare with paragraph documents only)
            # - Once for full-doc mode (compare with full-doc documents only)
            # This prevents cross-mode merging (paragraph topic merging with full-doc document)

            if document_mode == "both":
                print(f"\n{'='*80}")
                print("🔀 DUAL-MODE EMBEDDING SEARCH")
                print("   Running separate searches for paragraph and full-doc modes")
                print(f"{'='*80}")

                # Search for paragraph mode
                embedding_result_para = await embedding_node.execute(extract_result, existing_documents, mode_filter="paragraph")

                # Search for full-doc mode
                embedding_result_full = await embedding_node.execute(extract_result, existing_documents, mode_filter="full-doc")

                # Combine results - use paragraph as base and add full-doc info
                embedding_result = {
                    'results': {
                        'merge': embedding_result_para['results']['merge'] + embedding_result_full['results']['merge'],
                        'create': embedding_result_para['results']['create'],  # CREATE only needs one set
                        'verify': embedding_result_para['results']['verify'] + embedding_result_full['results']['verify']
                    },
                    'total_topics': embedding_result_para['total_topics'],
                    'merge_count': embedding_result_para['merge_count'] + embedding_result_full['merge_count'],
                    'create_count': embedding_result_para['create_count'],
                    'verify_count': embedding_result_para['verify_count'] + embedding_result_full['verify_count'],
                    'llm_calls_saved': embedding_result_para['llm_calls_saved'] + embedding_result_full['llm_calls_saved'],
                    'mode_filter': 'both',
                    'para_result': embedding_result_para,
                    'full_result': embedding_result_full
                }

                print(f"\n📊 Combined Results:")
                print(f"   Paragraph mode merges: {embedding_result_para['merge_count']}")
                print(f"   Full-doc mode merges: {embedding_result_full['merge_count']}")
                print(f"   Total merges: {embedding_result['merge_count']}")
                print(f"   Creates: {embedding_result['create_count']}")
            else:
                # Single mode - simple search
                mode_filter_for_search = document_mode
                embedding_result = await embedding_node.execute(extract_result, existing_documents, mode_filter=mode_filter_for_search)

            # Print status after embedding search
            self.print_status()

        # Node 3.5: LLM Verification (if there are uncertain topics)
        if embedding_result and embedding_result.get('verify_count', 0) > 0:
            verification_node = LLMVerificationNode()
            self.add_node(verification_node)

            # Verify uncertain topics and update embedding_result
            embedding_result = await verification_node.execute(embedding_result)

            # Print status after LLM verification
            self.print_status()

        # Node 4: Document Creator (if enabled and embedding search succeeded)
        if create_documents and embedding_result:
            document_node = DocumentCreatorNode()
            self.add_node(document_node)

            await document_node.execute(embedding_result, mode=document_mode)

            # Print status after document creation
            self.print_status()

        # Node 5: Document Merger (if enabled and embedding search has merge topics)
        if merge_documents and embedding_result:
            # Check if there are topics to merge
            if embedding_result.get('merge_count', 0) > 0:
                # Load existing documents for merging if not provided
                if existing_documents_para is None or existing_documents_full is None:
                    print(f"\n{'='*80}")
                    print("📚 Loading existing documents for merging")
                    print(f"{'='*80}")

                    try:
                        if USE_POSTGRESQL:
                            from chunked_document_database import ChunkedDocumentDatabase
                            db = ChunkedDocumentDatabase(
                                container_name=POSTGRES_CONTAINER,
                                database=POSTGRES_DATABASE
                            )

                            # Load paragraph mode documents
                            if existing_documents_para is None:
                                existing_documents_para = db.get_all_documents_with_embeddings(mode="paragraph")
                                print(f"✅ Loaded {len(existing_documents_para)} paragraph mode documents")

                            # Load full-doc mode documents
                            if existing_documents_full is None:
                                existing_documents_full = db.get_all_documents_with_embeddings(mode="full-doc")
                                print(f"✅ Loaded {len(existing_documents_full)} full-doc mode documents")
                        else:
                            from document_database import DocumentDatabase
                            db = DocumentDatabase(db_path="documents.db")

                            # Load paragraph mode documents
                            if existing_documents_para is None:
                                existing_documents_para = db.get_all_documents(mode="paragraph")
                                print(f"✅ Loaded {len(existing_documents_para)} paragraph mode documents")

                            # Load full-doc mode documents
                            if existing_documents_full is None:
                                existing_documents_full = db.get_all_documents(mode="full-doc")
                                print(f"✅ Loaded {len(existing_documents_full)} full-doc mode documents")

                    except FileNotFoundError:
                        print("ℹ️  Database file not found - cannot merge")
                        existing_documents_para = []
                        existing_documents_full = []
                    except Exception as e:
                        print(f"⚠️  Could not load documents for merging: {e}")
                        existing_documents_para = []
                        existing_documents_full = []

                    print(f"{'='*80}")

                merger_node = DocumentMergerNode()
                self.add_node(merger_node)

                await merger_node.execute(
                    embedding_result,
                    existing_documents_para=existing_documents_para,
                    existing_documents_full=existing_documents_full,
                    mode=document_mode
                )

                # Print status after merging
                self.print_status()

        self.end_time = datetime.now()

        # Print final summary
        self.print_summary()


async def main():
    """Example usage"""

    # Create workflow manager
    manager = WorkflowManager()

    # Run workflow
    await manager.run(
        start_url="https://docs.eosnetwork.com/docs/latest/quick-start/introduction",
        max_pages=1,  # Reduced for testing (save cost and time)
        same_domain_only=True,
        output_dir="bfs_crawled",
        extract_topics=True,
        embedding_search=True,  # Enable embedding search
        existing_documents=None,  # No existing documents (all will be marked for creation)
        create_documents=True,  # Enable document creation
        document_mode="both"  # Create both paragraph and full-doc versions
    )


if __name__ == "__main__":
    asyncio.run(main())
