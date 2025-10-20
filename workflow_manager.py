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

            # Prepare result
            result = {
                'crawler': crawler,
                'pages_crawled': len(crawler.successful),
                'pages_failed': len(crawler.failed),
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

    async def execute(self, extract_result: Dict, existing_documents: List[Dict] = None) -> Dict:
        """Execute embedding search"""
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

            # Initialize searcher
            print("✅ Embedding searcher initialized")
            searcher = EmbeddingSearcher()

            # Get all topics from extraction result
            all_topics = []
            for topics in extract_result['all_topics'].values():
                all_topics.extend(topics)

            print(f"📋 Processing {len(all_topics)} topics")

            # Use empty list if no existing documents provided
            if existing_documents is None:
                existing_documents = []
                print("ℹ️  No existing documents provided - all topics will be marked for creation")

            # Process topics
            results = searcher.batch_process_topics(all_topics, existing_documents)

            # Prepare result summary
            result = {
                'results': results,
                'total_topics': len(all_topics),
                'merge_count': len(results['merge']),
                'create_count': len(results['create']),
                'verify_count': len(results['verify']),
                'llm_calls_saved': len(results['merge']) + len(results['create'])
            }

            self.complete(result)
            return result

        except Exception as e:
            self.fail(str(e))
            raise


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

            # Also collect topics that need verification (we'll create docs for them too)
            for item in results['verify']:
                create_topics.append(item['topic'])

            if not create_topics:
                self.skip("No topics require document creation")
                return None

            print(f"📋 Creating documents for {len(create_topics)} topics")
            print(f"   Mode: {mode.upper()}")

            # Create documents based on mode
            if mode == "both":
                doc_results = creator.create_documents_both_modes(create_topics)
            elif mode == "paragraph":
                doc_results = creator.create_documents_batch(create_topics, mode="paragraph")
            elif mode == "full-doc":
                doc_results = creator.create_documents_batch(create_topics, mode="full-doc")
            else:
                raise ValueError(f"Invalid mode: {mode}")

            # Save documents (to files and database)
            creator.save_documents(doc_results, output_dir="documents", save_to_db=True, db_path="documents.db")

            # Prepare result
            result = {
                'mode': mode,
                'doc_results': doc_results,
                'total_topics': len(create_topics),
                'documents_created': doc_results.get('total_documents', doc_results.get('success_count', 0)),
                'failed_count': doc_results.get('fail_count', 0)
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
                merge_pairs = []
                for mt in merge_topics:
                    # Find corresponding documents
                    para_doc = self._find_document(mt['target_document']['id'], existing_documents_para)
                    full_doc = self._find_document(mt['target_document']['id'], existing_documents_full)

                    merge_pairs.append({
                        'topic': mt['topic'],
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
                elif node.name == "Document Creator":
                    print(f"   Mode: {node.result['mode']}, Documents: {node.result['documents_created']}")
                    if node.result.get('failed_count', 0) > 0:
                        print(f"   Failed: {node.result['failed_count']}")
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
                if document_node.result.get('failed_count', 0) > 0:
                    print(f"   Failed: {document_node.result['failed_count']}")
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
            embedding_node = EmbeddingSearchNode()
            self.add_node(embedding_node)

            embedding_result = await embedding_node.execute(extract_result, existing_documents)

            # Print status after embedding search
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
        max_pages=2,  # Reduced for testing (save cost and time)
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
