#!/usr/bin/env python3
"""
Simplified Workflow Manager

Orchestrates the crawling → topic extraction → document creation/merge workflow.
Removed dual-mode complexity - single unified approach.
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
        print(f"🔵  STEP: {self.name.upper()}")
        print(f"{'='*80}")
        print(f"📝  {self.description}")
        print(f"{'='*80}")

    def complete(self, result=None):
        """Mark node as completed"""
        self.status = NodeStatus.COMPLETED
        self.end_time = datetime.now()
        self.result = result
        duration = (self.end_time - self.start_time).total_seconds()
        print(f"\n✅  [{self.name}] Completed in {duration:.2f}s")

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
            crawler = BFSCrawler(
                start_url=start_url,
                max_pages=max_pages,
                same_domain_only=same_domain_only,
                output_dir=output_dir,
                extract_topics=False
            )

            await crawler.crawl_bfs()
            crawler.save_report()

            pages_crawled = len(crawler.successful)
            pages_failed = len(crawler.failed)

            if pages_crawled == 0:
                error_msg = f"Crawl failed: No pages successfully crawled"
                self.fail(error_msg)
                raise ValueError(error_msg)

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
            description="Extract topics with keywords and content from crawled pages"
        )

    async def execute(self, crawl_result: Dict) -> Dict:
        """Execute topic extraction"""
        from extract_topics import TopicExtractor

        self.start()

        try:
            if not crawl_result or not crawl_result.get('output_dir'):
                self.skip("No crawl result provided")
                return None

            if crawl_result.get('pages_crawled', 0) == 0:
                self.skip("No pages crawled")
                return None

            if not os.getenv('GEMINI_API_KEY'):
                self.skip("GEMINI_API_KEY not set")
                return None

            extractor = TopicExtractor()
            output_dir = str(crawl_result['output_dir'])
            all_topics = await extractor.extract_from_crawled_files(output_dir)

            if not all_topics:
                self.skip("No topics extracted")
                return None

            extractor.save_report(all_topics, f"{output_dir}/topics_report.txt")

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


class MergeDecisionNode(WorkflowNode):
    """Node for deciding whether to merge or create new documents"""

    def __init__(self):
        super().__init__(
            name="Merge Decision",
            description="Use multi-signal analysis to decide merge vs create"
        )

    async def execute(self, extract_result: Dict, existing_documents: List[Dict] = None) -> Dict:
        """
        Execute merge decision using multi-signal approach

        Args:
            extract_result: Result from topic extraction
            existing_documents: List of existing documents (optional)

        Returns:
            Decision results with topics categorized as merge/create
        """
        from merge_or_create_decision import MergeOrCreateDecision
        from embedding_search import EmbeddingSearcher  # For embedder
        import google.generativeai as genai

        self.start()

        try:
            if not os.getenv('GEMINI_API_KEY'):
                self.skip("GEMINI_API_KEY not set")
                return None

            if not extract_result or not extract_result.get('all_topics'):
                self.skip("No topics to process")
                return None

            # Initialize LLM for verification
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            llm_model_name = os.getenv('LLM_VERIFIER_MODEL', 'gemini-2.5-flash-lite')
            llm = genai.GenerativeModel(llm_model_name)

            # Initialize embedder for similarity checks
            embedder = EmbeddingSearcher()

            # Initialize decision maker with LLM support
            decision_maker = MergeOrCreateDecision(embedder=embedder, llm=llm)
            print("🤖  LLM verification: ENABLED (for uncertain cases)")
            print()  # Blank line for readability

            # Flatten all topics
            all_topics = []
            for topics in extract_result['all_topics'].values():
                all_topics.extend(topics)

            if len(all_topics) == 0:
                self.skip("No topics after flattening")
                return None

            print(f"📋  Analyzing {len(all_topics)} topics for merge/create decision...")

            # Use empty list if no existing documents
            if existing_documents is None:
                existing_documents = []
                print("ℹ️  No existing documents - all topics will be created")

            # Process each topic
            results = {'merge': [], 'create': [], 'verify': []}

            for topic in all_topics:
                decision = decision_maker.decide(topic, existing_documents, use_llm_verification=True)

                if decision['action'] == 'merge':
                    results['merge'].append({
                        'topic': topic,
                        'decision': decision
                    })
                elif decision['action'] == 'create':
                    results['create'].append({
                        'topic': topic,
                        'decision': decision
                    })
                else:  # verify
                    results['verify'].append({
                        'topic': topic,
                        'decision': decision
                    })

            result = {
                'results': results,
                'total_topics': len(all_topics),
                'merge_count': len(results['merge']),
                'create_count': len(results['create']),
                'verify_count': len(results['verify'])
            }

            self.complete(result)
            return result

        except Exception as e:
            self.fail(str(e))
            raise


class DocumentCreatorNode(WorkflowNode):
    """Node for creating documents from topics (simplified - no mode)"""

    def __init__(self):
        super().__init__(
            name="Document Creator",
            description="Create documents from topics with quality chunks"
        )

    async def execute(self, merge_result: Dict) -> Dict:
        """
        Execute document creation (simplified - single mode only)

        Args:
            merge_result: Result from merge decision node

        Returns:
            Document creation results
        """
        from document_creator import DocumentCreator

        self.start()

        try:
            if not os.getenv('GEMINI_API_KEY'):
                self.skip("GEMINI_API_KEY not set")
                return None

            if not merge_result or not merge_result.get('results'):
                self.skip("No merge results")
                return None

            creator = DocumentCreator()
            results = merge_result['results']

            # Collect topics that need document creation
            create_topics = [item['topic'] for item in results['create']]

            # Add verify topics as fallback (if LLM verification was skipped)
            verify_topics = results.get('verify', [])
            if verify_topics:
                print(f"   ⚠️  {len(verify_topics)} topics in verify state - creating as new documents")
                create_topics.extend([item['topic'] for item in verify_topics])

            if not create_topics:
                self.skip("No topics require creation")
                return None

            print(f"📝  Creating {len(create_topics)} new documents...")

            # Create documents (single mode - no paragraph/full-doc split)
            doc_results = creator.create_documents_batch(create_topics)
            all_documents = doc_results['documents']

            # Save to database
            if USE_POSTGRESQL:
                from chunked_document_database import ChunkedDocumentDatabase

                print("\n💾 Saving documents with chunks to PostgreSQL...")
                try:
                    db = ChunkedDocumentDatabase()
                    db_result = db.insert_documents_batch(all_documents)

                    saved_count = db_result.get('success_count', 0)
                    total_count = db_result.get('total', 0)

                    print(f"   ✅ Saved: {saved_count}/{total_count} documents")

                    if saved_count == 0:
                        error_msg = f"Database save failed: 0/{total_count} documents saved"
                        self.fail(error_msg)
                        raise RuntimeError(error_msg)

                except Exception as e:
                    print(f"   ❌ Database save failed: {e}")
                    self.fail(f"Database save failed: {e}")
                    raise
            else:
                print("\n💾 Saving to files (SQLite not supported for chunked documents)...")
                try:
                    creator.save_documents(doc_results, output_dir="documents", save_to_db=False)
                except Exception as e:
                    print(f"   ❌ File save failed: {e}")
                    self.fail(f"File save failed: {e}")
                    raise

            result = {
                'doc_results': doc_results,
                'total_topics': len(create_topics),
                'documents_created': doc_results.get('total_documents', 0)
            }

            self.complete(result)
            return result

        except Exception as e:
            self.fail(str(e))
            raise


class DocumentMergerNode(WorkflowNode):
    """Node for merging topics with existing documents (simplified - no mode)"""

    def __init__(self):
        super().__init__(
            name="Document Merger",
            description="Merge topics with existing documents and re-chunk"
        )

    async def execute(
        self,
        merge_result: Dict,
        existing_documents: List[Dict] = None
    ) -> Dict:
        """
        Execute document merging (simplified - single mode only)

        Args:
            merge_result: Result from merge decision node
            existing_documents: List of existing documents for merging

        Returns:
            Document merge results
        """
        from document_merger import DocumentMerger

        self.start()

        try:
            if not os.getenv('GEMINI_API_KEY'):
                self.skip("GEMINI_API_KEY not set")
                return None

            if not merge_result or not merge_result.get('results'):
                self.skip("No merge results")
                return None

            merger = DocumentMerger()
            results = merge_result['results']

            # Collect merge topics
            merge_topics = []
            for item in results['merge']:
                merge_topics.append({
                    'topic': item['topic'],
                    'target_doc_id': item['decision']['target_doc_id']
                })

            if not merge_topics:
                self.skip("No topics require merging")
                return None

            print(f"🔀  Merging {len(merge_topics)} topics with existing documents...")

            # Create merge pairs
            merge_pairs = []
            for mt in merge_topics:
                target_doc_id = mt['target_doc_id']
                if target_doc_id and existing_documents:
                    # Find the existing document by ID
                    target_doc = next((doc for doc in existing_documents if doc['id'] == target_doc_id), None)
                    if target_doc:
                        merge_pairs.append({
                            'topic': mt['topic'],
                            'existing_document': target_doc
                        })

            # Merge documents (single mode)
            merge_results = merger.merge_documents_batch(merge_pairs)

            # Save merged documents
            merger.save_merged_documents(
                merge_results,
                output_dir="merged_documents",
                save_to_db=True
            )

            result = {
                'merge_results': merge_results,
                'total_topics': len(merge_topics),
                'documents_merged': merge_results.get('total_merged', 0)
            }

            self.complete(result)
            return result

        except Exception as e:
            self.fail(str(e))
            raise


class WorkflowManager:
    """Manages the complete simplified workflow"""

    def __init__(self):
        self.nodes: List[WorkflowNode] = []
        self.start_time = None
        self.end_time = None

        # Initialize components once (reused across runs)
        self._components_initialized = False
        self.topic_extractor = None
        self.embedder = None
        self.llm = None
        self.decision_maker = None
        self.doc_creator = None
        self.doc_merger = None
        self.db = None

    def _initialize_components(self):
        """Initialize RAG pipeline components once"""
        if self._components_initialized:
            return

        from extract_topics import TopicExtractor
        from merge_or_create_decision import MergeOrCreateDecision
        from embedding_search import EmbeddingSearcher
        from document_creator import DocumentCreator
        from document_merger import DocumentMerger
        from chunked_document_database import SimpleDocumentDatabase
        import google.generativeai as genai

        print("🔧 Initializing RAG components...")

        self.topic_extractor = TopicExtractor()
        self.embedder = EmbeddingSearcher()
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        llm_model_name = os.getenv('LLM_VERIFIER_MODEL', 'gemini-2.5-flash-lite')
        self.llm = genai.GenerativeModel(llm_model_name)
        self.decision_maker = MergeOrCreateDecision(embedder=self.embedder, llm=self.llm)
        self.doc_creator = DocumentCreator()
        self.doc_merger = DocumentMerger()
        self.db = SimpleDocumentDatabase()

        self._components_initialized = True
        print(f"✅ Components initialized and ready for reuse")
        print(f"   LLM Verifier Model: {llm_model_name}")

    def add_node(self, node: WorkflowNode):
        """Add a node to the workflow"""
        self.nodes.append(node)

    def print_status(self):
        """Print current status of all nodes"""
        print(f"\n{'='*80}")
        print("📊  WORKFLOW PROGRESS")
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
                elif node.name == "Merge Decision":
                    print(f"   Merge: {node.result['merge_count']}, Create: {node.result['create_count']}, Verify: {node.result['verify_count']}")
                elif node.name == "Document Creator":
                    print(f"   Documents: {node.result['documents_created']}")
                elif node.name == "Document Merger":
                    print(f"   Documents: {node.result['documents_merged']}")

        print(f"{'='*80}")

    def print_summary(self):
        """Print final summary"""
        duration = (self.end_time - self.start_time).total_seconds()

        print(f"\n{'='*80}")
        print("✅  WORKFLOW COMPLETE!")
        print(f"{'='*80}")
        print(f"⏱️   Total Duration: {duration:.2f}s")
        print(f"\n📊  Summary:")

        for node in self.nodes:
            status_icon = {
                NodeStatus.COMPLETED: "✅",
                NodeStatus.FAILED: "❌",
                NodeStatus.SKIPPED: "⏭️ "
            }.get(node.status, "⏸️ ")

            print(f"   {status_icon} {node.name}: {node.status.value}")

        print(f"{'='*80}")

    async def _process_pages_iteratively(
        self,
        crawl_result: Dict,
        merge_decision: bool,
        create_documents: bool,
        merge_documents: bool
    ):
        """
        Process pages iteratively: extract -> decide -> save for each page

        This allows topics from later pages to merge with documents created from earlier pages
        """
        # Use pre-initialized components (much faster!)
        self._initialize_components()

        # Get list of crawled pages from the saved file
        import json
        output_dir = crawl_result.get('output_dir', 'bfs_crawled')
        crawl_data_file = os.path.join(output_dir, 'crawl_data.json')

        with open(crawl_data_file, 'r') as f:
            crawl_session_data = json.load(f)

        crawled_data = crawl_session_data.get('crawl_data', {})

        total_pages = len(crawled_data)
        total_docs_created = 0
        total_docs_merged = 0

        # Process each page individually
        for page_num, (url, page_data) in enumerate(crawled_data.items(), 1):
            if not page_data.get('success'):
                print(f"⏭️   Skipping page {page_num}/{total_pages} (failed crawl): {url[:60]}...")
                continue

            # Start timing this page
            page_start_time = datetime.now()

            print(f"\n{'='*80}")
            print(f"📄  PAGE {page_num}/{total_pages}: {url[:60]}...")
            print(f"{'='*80}")

            try:
                # Begin transaction for atomic page processing
                self.db.begin_transaction()

                # Step 1: Extract topics from this page
                print(f"🔍  Step 1: Extracting topics...")
                markdown_content = page_data.get('markdown', '')
                topics = await self.topic_extractor.extract_topics_from_text(markdown_content, url)

                if not topics:
                    print(f"   ⏭️   No topics extracted, skipping page")
                    self.db.rollback_transaction()
                    continue

                print(f"   ✅  Extracted {len(topics)} topics")

                # Step 2: Load current documents from database
                print(f"🔍  Step 2: Loading existing documents from database...")
                existing_docs = self.db.get_all_documents_with_embeddings()
                print(f"   📊  Found {len(existing_docs)} existing documents")

                # Step 3: Merge decision for each topic
                print(f"🤖  Step 3: Analyzing merge/create decisions...")
                merge_topics = []
                create_topics = []

                for topic in topics:
                    decision = self.decision_maker.decide(topic, existing_docs, use_llm_verification=True)
                    if decision['action'] == 'merge':
                        merge_topics.append({
                            'topic': topic,
                            'decision': decision
                        })
                    else:  # create
                        create_topics.append(topic)

                print(f"   📊  Decisions: {len(merge_topics)} merge, {len(create_topics)} create")

                # Step 4: Create new documents
                if create_topics and create_documents:
                    print(f"📝  Step 4a: Creating {len(create_topics)} new documents...")
                    doc_results = self.doc_creator.create_documents_batch(create_topics)
                    new_docs = doc_results['documents']

                    # Save to database
                    if new_docs:
                        save_result = self.db.insert_documents_batch(new_docs)
                        total_docs_created += save_result['success_count']
                        print(f"   ✅  Saved {save_result['success_count']}/{len(new_docs)} documents")

                # Step 5: Merge documents (SEQUENTIAL to handle same-document merges)
                if merge_topics and merge_documents:
                    print(f"🔀  Step 4b: Merging {len(merge_topics)} topics with existing documents...")

                    # Group topics by target document ID
                    from collections import defaultdict
                    topics_by_doc = defaultdict(list)
                    for mt in merge_topics:
                        target_doc_id = mt['decision']['target_doc_id']
                        topics_by_doc[target_doc_id].append(mt)

                    print(f"   📊 Merging into {len(topics_by_doc)} unique documents")

                    # Process each document sequentially
                    for doc_id, merge_list in topics_by_doc.items():
                        doc_title = merge_list[0]['decision'].get('target_doc_title', 'Unknown')
                        print(f"\n   📄 Document: '{doc_title}'")
                        print(f"      Topics to merge: {len(merge_list)}")

                        # Load document ONCE
                        current_doc = self.db.get_document_by_id(doc_id)
                        if not current_doc:
                            print(f"      ⚠️  Document not found, skipping")
                            continue

                        # BATCH MERGE: Merge ALL topics at once (5x cost reduction!)
                        # OLD: Loop N times, call merge_document N times → 5 LLM calls + 124 embeddings = $0.35
                        # NEW: Call merge_multiple_topics_into_document ONCE → 1 LLM call + 30 embeddings = $0.08
                        print(f"      🚀 Using BATCH MERGE for {len(merge_list)} topics (5x cost reduction!)")

                        topics = [mt['topic'] for mt in merge_list]
                        merged_doc = self.doc_merger.merge_multiple_topics_into_document(topics, current_doc)

                        if merged_doc:
                            current_doc = merged_doc
                            print(f"      ✅ SUCCESS: Merged {len(merge_list)} topics in ONE operation!")
                            print(f"               Final content: {len(merged_doc.get('content', ''))} chars")
                        else:
                            print(f"      ❌ FAILED: Batch merge failed, skipping document")
                            continue

                        # Save final merged document (after all topics merged)
                        if current_doc != self.db.get_document_by_id(doc_id):  # Check if changed
                            self.db.update_document_with_chunks(current_doc)
                            total_docs_merged += 1
                            print(f"      ✅ Saved with {len(merge_list)} topics merged")

                    print(f"\n   ✅  Updated {total_docs_merged} documents total")

                # Commit transaction - all operations succeeded
                self.db.commit_transaction()

                # Page timing
                page_duration = (datetime.now() - page_start_time).total_seconds()
                print(f"✅  Page {page_num}/{total_pages} complete! ⏱️  {page_duration:.2f}s")

            except Exception as e:
                # Rollback transaction on any error
                self.db.rollback_transaction()
                page_duration = (datetime.now() - page_start_time).total_seconds()
                print(f"❌ Page {page_num}/{total_pages} failed! ⏱️  {page_duration:.2f}s")
                print(f"   Error: {str(e)}")
                print(f"   ⚠️  All changes rolled back")

        print(f"\n{'='*80}")
        print(f"✅  ITERATIVE PROCESSING COMPLETE")
        print(f"{'='*80}")
        print(f"📊  Total Results:")
        print(f"   • Pages processed: {total_pages}")
        print(f"   • Documents created: {total_docs_created}")
        print(f"   • Documents merged: {total_docs_merged}")
        print(f"{'='*80}")

    async def run(
        self,
        start_url: str,
        max_pages: int = 50,
        same_domain_only: bool = True,
        output_dir: str = "bfs_crawled",
        extract_topics: bool = True,
        merge_decision: bool = True,
        existing_documents: List[Dict] = None,
        create_documents: bool = True,
        merge_documents: bool = True
    ):
        """
        Run the complete simplified workflow (no dual-mode complexity)

        Args:
            start_url: URL to start crawling from
            max_pages: Maximum pages to crawl
            same_domain_only: Only crawl same domain
            output_dir: Output directory
            extract_topics: Whether to extract topics
            merge_decision: Whether to run merge decision analysis
            existing_documents: List of existing documents for comparison
            create_documents: Whether to create documents from topics
            merge_documents: Whether to merge topics with existing documents
        """
        self.start_time = datetime.now()

        print(f"\n{'='*80}")
        print("🚀  WORKFLOW MANAGER - RAG PIPELINE")
        print(f"{'='*80}")
        print(f"🌐  Start URL:      {start_url}")
        print(f"📄  Max Pages:      {max_pages}")
        print(f"📁  Output Dir:     {output_dir}")
        print(f"🏷️   Extract Topics: {extract_topics}")
        print(f"{'='*80}")

        # Node 1: Crawl
        crawl_node = CrawlNode()
        self.add_node(crawl_node)
        crawl_result = await crawl_node.execute(start_url, max_pages, same_domain_only, output_dir)

        if not crawl_result or crawl_node.status == NodeStatus.FAILED:
            print("\n❌ Crawl failed - cannot continue workflow")
            self.end_time = datetime.now()
            self.print_summary()
            return

        self.print_status()

        # Process pages iteratively (extract -> decide -> save for each page)
        if extract_topics:
            print(f"\n{'='*80}")
            print("🔄  ITERATIVE PROCESSING MODE")
            print(f"{'='*80}")
            print("📝  Processing each page individually:")
            print("    1. Extract topics from page")
            print("    2. Decide merge/create against existing DB docs")
            print("    3. Create/merge documents")
            print("    4. Save to database immediately")
            print("    5. Move to next page (can now merge with previous pages)")
            print(f"{'='*80}\n")

            await self._process_pages_iteratively(
                crawl_result,
                merge_decision,
                create_documents,
                merge_documents
            )

            self.end_time = datetime.now()
            self.print_summary()
            return

        # Fallback: Old batch mode if not extracting topics
        # Node 2: Extract Topics
        extract_result = None
        if extract_topics:
            extract_node = ExtractTopicsNode()
            self.add_node(extract_node)
            extract_result = await extract_node.execute(crawl_result)
            self.print_status()

        # Node 3: Merge Decision
        merge_result = None
        if merge_decision and extract_result:
            # Load existing documents if not provided
            if existing_documents is None:
                if USE_POSTGRESQL:
                    print(f"\n{'='*80}")
                    print("📚 Loading existing documents from PostgreSQL")
                    print(f"{'='*80}")

                    try:
                        from chunked_document_database import ChunkedDocumentDatabase
                        db = ChunkedDocumentDatabase(
                            container_name=POSTGRES_CONTAINER,
                            database=POSTGRES_DATABASE
                        )
                        existing_documents = db.get_all_documents_with_embeddings()

                        if existing_documents:
                            print(f"✅ Loaded {len(existing_documents)} existing documents")
                        else:
                            print("ℹ️  No existing documents found")
                            existing_documents = []

                    except Exception as e:
                        print(f"⚠️  Could not load existing documents: {e}")
                        existing_documents = []

                    print(f"{'='*80}")
                else:
                    print("ℹ️  SQLite mode - treating as first run")
                    existing_documents = []

            decision_node = MergeDecisionNode()
            self.add_node(decision_node)
            merge_result = await decision_node.execute(extract_result, existing_documents)
            self.print_status()

        # Node 4: Document Creator
        if create_documents and merge_result:
            creator_node = DocumentCreatorNode()
            self.add_node(creator_node)
            await creator_node.execute(merge_result)
            self.print_status()

        # Node 5: Document Merger
        if merge_documents and merge_result:
            if merge_result.get('merge_count', 0) > 0:
                # Need existing documents for merging
                if existing_documents is None:
                    print(f"\n{'='*80}")
                    print("📚 Loading documents for merging")
                    print(f"{'='*80}")

                    try:
                        if USE_POSTGRESQL:
                            from chunked_document_database import ChunkedDocumentDatabase
                            db = ChunkedDocumentDatabase()
                            existing_documents = db.get_all_documents_with_embeddings()
                            print(f"✅ Loaded {len(existing_documents)} documents")
                        else:
                            print("ℹ️  SQLite not supported for merging")
                            existing_documents = []

                    except Exception as e:
                        print(f"⚠️  Could not load documents: {e}")
                        existing_documents = []

                    print(f"{'='*80}")

                merger_node = DocumentMergerNode()
                self.add_node(merger_node)
                await merger_node.execute(merge_result, existing_documents)
                self.print_status()

        self.end_time = datetime.now()
        self.print_summary()


async def main():
    """Example usage"""
    manager = WorkflowManager()

    await manager.run(
        start_url="https://help.tokenpocket.pro/en/wallet-operation/how-to-create-a-wallet/eos",
        max_pages=1,
        same_domain_only=True,
        output_dir="bfs_crawled",
        extract_topics=True,
        merge_decision=True,
        existing_documents=None,
        create_documents=True,
        merge_documents=True
    )


if __name__ == "__main__":
    asyncio.run(main())
