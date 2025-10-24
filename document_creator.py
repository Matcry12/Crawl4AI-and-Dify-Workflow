#!/usr/bin/env python3
"""
Document Creator Module

Creates documents from topics in two modes:
1. Paragraph mode: Concise, single-paragraph format
2. Full-doc mode: Comprehensive, well-structured document
"""

import os

# Suppress gRPC warnings (must be set BEFORE importing genai)
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

from typing import List, Dict, Optional
import google.generativeai as genai
from datetime import datetime
from hybrid_chunker import HybridChunker
from utils.rate_limiter import get_llm_rate_limiter, get_embedding_rate_limiter


class DocumentCreator:
    """
    Creates documents from topics using LLM
    Supports two modes: paragraph and full-doc
    """

    def __init__(self, api_key: str = None, model_name: str = None):
        """
        Initialize document creator

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model_name: Model to use (defaults to DOCUMENT_CREATOR_MODEL env var)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model_name = model_name or os.getenv('DOCUMENT_CREATOR_MODEL', 'gemini-2.5-flash-lite')

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Please set it in .env file")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

        # Rate limiters
        self.llm_limiter = get_llm_rate_limiter()
        self.embedding_limiter = get_embedding_rate_limiter()

        # Initialize hybrid chunker
        self.chunker = HybridChunker(api_key=self.api_key)

        print("✅ Document creator initialized")
        print(f"   Model: {self.model_name}")
        print(f"   Embedding model: text-embedding-004")
        print(f"   Hybrid chunker: enabled")

    def create_embedding(self, text: str) -> list:
        """
        Create embedding for text using Gemini

        Args:
            text: Text to embed (typically content or summary)

        Returns:
            768-dimensional embedding vector
        """
        try:
            self.embedding_limiter.wait_if_needed()
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"  ⚠️  Embedding generation failed: {e}")
            return None

    def create_paragraph_document(self, topic: Dict) -> Dict:
        """
        Create a concise paragraph-style document

        Args:
            topic: Topic dictionary with title, summary, description

        Returns:
            Document dictionary with metadata and content
        """
        prompt = f"""Create a concise, single-paragraph document from this topic.

Topic: {topic['title']}
Category: {topic['category']}
Summary: {topic['summary']}

Description:
{topic['description']}

Instructions:
1. Write a single, well-structured paragraph (4-8 sentences)
2. Cover the most important points from the description
3. Be clear and informative
4. Use professional tone
5. Do NOT include title or headings
6. Just write the paragraph content

Output only the paragraph text, nothing else.
"""

        try:
            print(f"\n  📝 Creating paragraph document for: {topic['title']}")

            self.llm_limiter.wait_if_needed()
            response = self.model.generate_content(prompt)
            content = response.text.strip()

            # Generate embedding for the content
            print(f"  🔢 Generating embedding...")
            embedding = self.create_embedding(content)

            # Create document ID
            safe_title = topic['title'].lower().replace(' ', '_').replace(':', '').replace('/', '_')
            doc_id = f"{safe_title}_paragraph"

            document = {
                "id": doc_id,
                "title": topic['title'],
                "category": topic['category'],
                "mode": "paragraph",
                "content": content,
                "embedding": embedding,  # Add embedding!
                "created_at": datetime.now().isoformat(),
                "source_topic": {
                    "title": topic['title'],
                    "summary": topic['summary']
                }
            }

            emb_status = "✓" if embedding else "✗"
            print(f"  ✅ Paragraph created ({len(content)} chars, embedding: {emb_status})")
            return document

        except Exception as e:
            print(f"  ❌ Error creating paragraph: {e}")
            return None

    def create_fulldoc_document(self, topic: Dict) -> Dict:
        """
        Create a comprehensive full-document

        Args:
            topic: Topic dictionary with title, summary, description

        Returns:
            Document dictionary with metadata and content
        """
        prompt = f"""Create a comprehensive, well-structured document from this topic.

Topic: {topic['title']}
Category: {topic['category']}
Summary: {topic['summary']}

Description:
{topic['description']}

Instructions:
1. Create a complete, well-organized document
2. Include ALL important information from the description
3. Use proper markdown formatting:
   - Use ## for main sections
   - Use ### for subsections
   - Use bullet points and numbered lists where appropriate
   - Use **bold** for emphasis
   - Use `code` formatting for technical terms
4. Structure the document logically with sections
5. Be comprehensive but clear
6. Do NOT include the main title (# Title) - start with sections
7. Professional and informative tone

Output the complete markdown document.
"""

        try:
            print(f"\n  📄 Creating full document for: {topic['title']}")

            self.llm_limiter.wait_if_needed()
            response = self.model.generate_content(prompt)
            content = response.text.strip()

            # Generate embedding for the content
            print(f"  🔢 Generating embedding...")
            embedding = self.create_embedding(content)

            # Create document ID
            safe_title = topic['title'].lower().replace(' ', '_').replace(':', '').replace('/', '_')
            doc_id = f"{safe_title}_full-doc"

            document = {
                "id": doc_id,
                "title": topic['title'],
                "category": topic['category'],
                "mode": "full-doc",
                "content": content,
                "embedding": embedding,  # Add embedding!
                "created_at": datetime.now().isoformat(),
                "source_topic": {
                    "title": topic['title'],
                    "summary": topic['summary']
                }
            }

            emb_status = "✓" if embedding else "✗"
            print(f"  ✅ Full document created ({len(content)} chars, embedding: {emb_status})")
            return document

        except Exception as e:
            print(f"  ❌ Error creating full document: {e}")
            return None

    def create_document(self, topic: Dict, mode: str = "paragraph", enable_chunking: bool = True) -> Dict:
        """
        Create document in specified mode

        Args:
            topic: Topic dictionary
            mode: "paragraph" or "full-doc"
            enable_chunking: If True, apply semantic chunking to document

        Returns:
            Document dictionary (with 'chunks' key if enable_chunking=True)
        """
        if mode == "paragraph":
            document = self.create_paragraph_document(topic)
        elif mode == "full-doc":
            document = self.create_fulldoc_document(topic)
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'paragraph' or 'full-doc'")

        # Apply semantic chunking if enabled
        if enable_chunking and document:
            print(f"  🔪 Applying semantic chunking...")
            try:
                chunks = self.chunker.chunk_document(
                    content=document['content'],
                    document_id=document['id'],
                    title=document['title'],
                    mode=mode
                )
                document['chunks'] = chunks
                print(f"  ✅ Chunking complete: {chunks['stats']['total_sections']} sections, {chunks['stats']['total_propositions']} propositions")
            except Exception as e:
                print(f"  ⚠️  Chunking failed: {e}")
                document['chunks'] = None

        return document

    def create_documents_batch(
        self,
        topics: List[Dict],
        mode: str = "paragraph",
        enable_chunking: bool = True
    ) -> Dict:
        """
        Create multiple documents in batch

        Args:
            topics: List of topic dictionaries
            mode: "paragraph" or "full-doc"
            enable_chunking: If True, apply semantic chunking to each document

        Returns:
            Results dictionary with created documents and statistics
        """
        print(f"\n{'='*80}")
        print(f"📚 BATCH DOCUMENT CREATION ({mode.upper()} mode)")
        print(f"{'='*80}")
        print(f"Topics to process: {len(topics)}")

        documents = []
        failed = []

        for i, topic in enumerate(topics, 1):
            print(f"\n[{i}/{len(topics)}] Processing: {topic['title']}")

            doc = self.create_document(topic, mode, enable_chunking=enable_chunking)

            if doc:
                documents.append(doc)
            else:
                failed.append(topic['title'])

        # Print summary
        self._print_batch_summary(documents, failed, mode)

        return {
            "mode": mode,
            "documents": documents,
            "failed": failed,
            "success_count": len(documents),
            "fail_count": len(failed),
            "total": len(topics)
        }

    def create_documents_both_modes(
        self,
        topics: List[Dict]
    ) -> Dict:
        """
        Create documents in BOTH modes for each topic

        Args:
            topics: List of topic dictionaries

        Returns:
            Results dictionary with both paragraph and full-doc versions
        """
        print(f"\n{'='*80}")
        print(f"📚 CREATING DOCUMENTS IN BOTH MODES")
        print(f"{'='*80}")
        print(f"Topics to process: {len(topics)}")
        print(f"Total documents to create: {len(topics) * 2}")

        paragraph_docs = []
        fulldoc_docs = []
        failed = []

        for i, topic in enumerate(topics, 1):
            print(f"\n{'='*80}")
            print(f"[{i}/{len(topics)}] Processing: {topic['title']}")
            print(f"{'='*80}")

            # Create paragraph version (with chunking)
            print(f"\n  🔹 MODE 1: Paragraph")
            para_doc = self.create_document(topic, mode="paragraph", enable_chunking=True)
            if para_doc:
                paragraph_docs.append(para_doc)
            else:
                failed.append(f"{topic['title']} (paragraph)")

            # Create full-doc version (with chunking)
            print(f"\n  🔹 MODE 2: Full Document")
            full_doc = self.create_document(topic, mode="full-doc", enable_chunking=True)
            if full_doc:
                fulldoc_docs.append(full_doc)
            else:
                failed.append(f"{topic['title']} (full-doc)")

        # Print summary
        self._print_both_modes_summary(paragraph_docs, fulldoc_docs, failed, len(topics))

        return {
            "paragraph_documents": paragraph_docs,
            "fulldoc_documents": fulldoc_docs,
            "failed": failed,
            "paragraph_count": len(paragraph_docs),
            "fulldoc_count": len(fulldoc_docs),
            "fail_count": len(failed),
            "total_topics": len(topics),
            "total_documents": len(paragraph_docs) + len(fulldoc_docs)
        }

    def _print_batch_summary(self, documents: List[Dict], failed: List[str], mode: str):
        """Print batch creation summary"""
        print(f"\n{'='*80}")
        print(f"📊 BATCH CREATION SUMMARY ({mode.upper()})")
        print(f"{'='*80}")

        print(f"\n✅ Success: {len(documents)}")

        # Calculate chunk statistics
        total_sections = 0
        total_propositions = 0
        docs_with_chunks = 0

        if documents:
            for doc in documents:
                has_chunks = 'chunks' in doc and doc['chunks']
                chunk_info = ""
                if has_chunks:
                    docs_with_chunks += 1
                    stats = doc['chunks']['stats']
                    total_sections += stats['total_sections']
                    total_propositions += stats['total_propositions']
                    chunk_info = f" → {stats['total_sections']} sections, {stats['total_propositions']} props"
                print(f"   • {doc['title']} ({len(doc['content'])} chars{chunk_info})")

        if failed:
            print(f"\n❌ Failed: {len(failed)}")
            for title in failed:
                print(f"   • {title}")

        if docs_with_chunks > 0:
            print(f"\n🔪 Chunking Statistics:")
            print(f"   Documents chunked: {docs_with_chunks}/{len(documents)}")
            print(f"   Total sections: {total_sections}")
            print(f"   Total propositions: {total_propositions}")
            print(f"   Avg sections/doc: {total_sections/docs_with_chunks:.1f}")
            print(f"   Avg props/doc: {total_propositions/docs_with_chunks:.1f}")

        print(f"\n{'='*80}")

    def _print_both_modes_summary(
        self,
        paragraph_docs: List[Dict],
        fulldoc_docs: List[Dict],
        failed: List[str],
        total_topics: int
    ):
        """Print summary for both modes creation"""
        print(f"\n{'='*80}")
        print(f"📊 DUAL-MODE CREATION SUMMARY")
        print(f"{'='*80}")

        print(f"\nTopics processed: {total_topics}")
        print(f"Total documents created: {len(paragraph_docs) + len(fulldoc_docs)}")

        print(f"\n📝 PARAGRAPH MODE: {len(paragraph_docs)} documents")
        if paragraph_docs:
            for doc in paragraph_docs:
                print(f"   • {doc['title']} ({len(doc['content'])} chars)")

        print(f"\n📄 FULL-DOC MODE: {len(fulldoc_docs)} documents")
        if fulldoc_docs:
            for doc in fulldoc_docs:
                print(f"   • {doc['title']} ({len(doc['content'])} chars)")

        if failed:
            print(f"\n❌ FAILED: {len(failed)}")
            for title in failed:
                print(f"   • {title}")

        print(f"\n{'='*80}")

    def save_documents(self, results: Dict, output_dir: str = "documents", save_to_db: bool = True, db_path: str = "documents.db"):
        """
        Save documents to files and optionally to vector database

        Args:
            results: Results from create_documents_batch or create_documents_both_modes
            output_dir: Output directory for markdown files
            save_to_db: Whether to save to vector database
            db_path: Path to database file
        """
        import json
        from pathlib import Path

        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Determine what type of results we have
        if "paragraph_documents" in results:
            # Both modes
            mode = "both"
            all_docs = results["paragraph_documents"] + results["fulldoc_documents"]
        else:
            # Single mode
            mode = results["mode"]
            all_docs = results["documents"]

        # Save to vector database if enabled
        if save_to_db:
            print(f"\n💾 Saving {len(all_docs)} documents to vector database...")
            try:
                # Check if using PostgreSQL
                use_postgresql = os.getenv('USE_POSTGRESQL', 'true').lower() == 'true'

                if use_postgresql:
                    from document_database_docker import DocumentDatabaseDocker
                    db = DocumentDatabaseDocker()
                else:
                    from document_database import DocumentDatabase
                    db = DocumentDatabase(db_path=db_path)

                success_count = 0
                skipped_count = 0
                updated_count = 0

                for doc in all_docs:
                    # Check if document already exists
                    existing = db.get_document(doc['id'])

                    if existing:
                        # Document exists - check if we should update
                        if doc.get('embedding') and not existing.get('embedding'):
                            # New document has embedding but existing doesn't - update
                            print(f"  🔄 Updating {doc['id']} (adding embedding)")
                            if use_postgresql:
                                # For PostgreSQL, we need to use update logic
                                # This is handled by ON CONFLICT in create_document
                                if db.create_document(
                                    doc_id=doc['id'],
                                    title=doc['title'],
                                    content=doc['content'],
                                    category=doc.get('category'),
                                    mode=doc.get('mode'),
                                    embedding=doc.get('embedding'),
                                    metadata=doc.get('source_topic', {})
                                ):
                                    updated_count += 1
                            else:
                                # SQLite update
                                db.update_document(doc['id'], embedding=doc['embedding'])
                                updated_count += 1
                        else:
                            # Document exists and no update needed
                            print(f"  ⊘ Skipping {doc['id']} (already exists)")
                            skipped_count += 1
                    else:
                        # New document - insert
                        if use_postgresql:
                            if db.create_document(
                                doc_id=doc['id'],
                                title=doc['title'],
                                content=doc['content'],
                                category=doc.get('category'),
                                mode=doc.get('mode'),
                                embedding=doc.get('embedding'),
                                metadata=doc.get('source_topic', {})
                            ):
                                success_count += 1
                        else:
                            if db.insert_document(doc):
                                success_count += 1

                print(f"\n  ✅ Saved: {success_count} new documents")
                if updated_count > 0:
                    print(f"  🔄 Updated: {updated_count} documents")
                if skipped_count > 0:
                    print(f"  ⊘ Skipped: {skipped_count} duplicates")

                # Print statistics
                if hasattr(db, 'print_statistics'):
                    db.print_statistics()
                elif hasattr(db, 'get_statistics'):
                    stats = db.get_statistics()
                    print(f"\n  📊 Database Statistics:")
                    print(f"     Total documents: {stats['total_documents']}")
                    print(f"     With embeddings: {stats['documents_with_embeddings']}")

            except Exception as e:
                print(f"  ❌ Database save error: {e}")
                import traceback
                traceback.print_exc()

        # Save each document as markdown
        for doc in all_docs:
            # Create safe filename
            safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_'
                                for c in doc['title'])
            safe_title = safe_title.replace(' ', '_').lower()

            filename = f"{safe_title}_{doc['mode']}.md"
            filepath = Path(output_dir) / filename

            # Write document
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {doc['title']}\n\n")
                f.write(f"**Category**: {doc['category']}\n")
                f.write(f"**Mode**: {doc['mode']}\n")
                f.write(f"**Created**: {doc['created_at']}\n\n")
                f.write("---\n\n")
                f.write(doc['content'])
                f.write("\n")

        # Save summary as JSON
        summary_file = Path(output_dir) / "documents_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n📁 Markdown files saved to: {output_dir}/")
        print(f"   Files: {len(all_docs)}")
        print(f"   Summary: documents_summary.json")


# Example usage and testing
async def main():
    """Test document creator"""
    print("="*80)
    print("📚 Document Creator Test")
    print("="*80)

    # Initialize creator
    try:
        creator = DocumentCreator()
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        return

    # Example topics (from previous extraction)
    topics = [
        {
            "title": "Python Bug Reporting",
            "category": "guide",
            "summary": "Learn how to report bugs in Python using the GitHub issue tracker.",
            "description": "Issue reports for Python should be submitted via the GitHub issues tracker at https://github.com/python/cpython/issues. Before filing a report, search the tracker to see if the problem has already been reported. If not, log in to GitHub and click 'New issue'. Provide a short title (under 10 words) and detailed comment describing the problem, expected vs actual behavior, any extension modules involved, and hardware/software platform details."
        },
        {
            "title": "Python Community Support",
            "category": "community",
            "summary": "Engage with the Python community through newsgroups and mailing lists.",
            "description": "For Python-related questions, you can post to the newsgroup comp.lang.python or send to the mailing list at python-list@python.org. These are gatewayed, so messages posted to one are forwarded to the other. Check the FAQ before posting at https://docs.python.org/3/faq/index.html."
        }
    ]

    # Test 1: Create paragraph documents
    print("\n" + "="*80)
    print("TEST 1: PARAGRAPH MODE")
    print("="*80)
    para_results = creator.create_documents_batch(topics, mode="paragraph")

    # Test 2: Create full-doc documents
    print("\n" + "="*80)
    print("TEST 2: FULL-DOC MODE")
    print("="*80)
    full_results = creator.create_documents_batch(topics, mode="full-doc")

    # Test 3: Create both modes
    print("\n" + "="*80)
    print("TEST 3: BOTH MODES")
    print("="*80)
    both_results = creator.create_documents_both_modes(topics)

    # Save documents
    creator.save_documents(both_results, output_dir="test_documents")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
