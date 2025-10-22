#!/usr/bin/env python3
"""
Search Knowledge Base

Usage:
    python search_kb.py "your search query"
    or just run: python search_kb.py
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()

def search_simple(query, top_k=5):
    """Simple keyword search using docker exec"""
    import subprocess

    print(f"\n🔍 Searching: {query}")
    print("=" * 80)

    # Search using SQL LIKE
    sql = f"""
        SELECT topic_title, category, mode,
               LEFT(content, 200) as preview,
               LENGTH(content) as length
        FROM documents
        WHERE content ILIKE '%{query}%'
        ORDER BY created_at DESC
        LIMIT {top_k};
    """

    result = subprocess.run(
        ['docker', 'exec', 'docker-db-1', 'psql', '-U', 'postgres', '-d', 'crawl4ai', '-c', sql],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(f"❌ Search failed: {result.stderr}")
        return False

def search_semantic(query, top_k=5):
    """Semantic search using embeddings (requires psycopg2 and direct connection)"""
    try:
        import psycopg2
        from core.gemini_embeddings import GeminiEmbeddings

        print(f"\n🔍 Semantic Search: {query}")
        print("=" * 80)

        # Generate query embedding
        print("  → Generating query embedding...")
        embedder = GeminiEmbeddings(api_key=os.getenv('GEMINI_API_KEY'))
        query_emb = embedder.embed_query(query)
        print("  ✅ Embedding generated")

        # Connect to database via Docker exec (workaround for no port mapping)
        # Note: This won't work directly, so we'll use docker exec method
        print("\n  ℹ️  For semantic search, PostgreSQL port needs to be exposed")
        print("  Using keyword search instead...")
        return search_simple(query, top_k)

    except ImportError:
        print("  ℹ️  psycopg2 not available, using keyword search...")
        return search_simple(query, top_k)
    except Exception as e:
        print(f"  ℹ️  Semantic search unavailable: {e}")
        print("  Using keyword search instead...")
        return search_simple(query, top_k)

def list_all_documents():
    """List all documents in the knowledge base"""
    import subprocess

    print("\n📚 All Documents in Knowledge Base")
    print("=" * 80)

    sql = """
        SELECT topic_title, category, mode,
               LENGTH(content) as length,
               created_at
        FROM documents
        ORDER BY topic_title, mode;
    """

    result = subprocess.run(
        ['docker', 'exec', 'docker-db-1', 'psql', '-U', 'postgres', '-d', 'crawl4ai', '-c', sql],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(result.stdout)

        # Get count by category
        print("\n📊 Documents by Category:")
        sql = """
            SELECT category, COUNT(*) as count
            FROM documents
            GROUP BY category
            ORDER BY count DESC;
        """
        result = subprocess.run(
            ['docker', 'exec', 'docker-db-1', 'psql', '-U', 'postgres', '-d', 'crawl4ai', '-c', sql],
            capture_output=True,
            text=True
        )
        print(result.stdout)

def show_document(title):
    """Show full content of a document"""
    import subprocess

    print(f"\n📄 Document: {title}")
    print("=" * 80)

    sql = f"""
        SELECT mode, content
        FROM documents
        WHERE topic_title ILIKE '%{title}%'
        ORDER BY mode;
    """

    result = subprocess.run(
        ['docker', 'exec', 'docker-db-1', 'psql', '-U', 'postgres', '-d', 'crawl4ai', '-c', sql],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"❌ Document not found")

def main():
    print("=" * 80)
    print("🔍 Knowledge Base Search")
    print("=" * 80)

    # Check if query provided
    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
        search_simple(query)
    else:
        # Interactive mode
        print("\nWhat would you like to do?")
        print("  1. Search by keyword")
        print("  2. List all documents")
        print("  3. Show specific document")
        print("  q. Quit")

        while True:
            choice = input("\nChoice (1-3 or q): ").strip()

            if choice == 'q':
                print("👋 Goodbye!")
                break
            elif choice == '1':
                query = input("Search query: ").strip()
                if query:
                    search_simple(query)
            elif choice == '2':
                list_all_documents()
            elif choice == '3':
                title = input("Document title (partial match): ").strip()
                if title:
                    show_document(title)
            else:
                print("Invalid choice. Try again.")

    print("\n" + "=" * 80)
    print("💡 Tips:")
    print("  - Add more docs: python build_kb.py")
    print("  - Direct DB access: docker exec -it docker-db-1 psql -U postgres -d crawl4ai")
    print("=" * 80)

if __name__ == "__main__":
    main()
