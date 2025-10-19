#!/usr/bin/env python3
"""
Example: Using the Unified Pipeline

This example shows how to use the unified pipeline to:
1. Crawl a webpage
2. Extract topics with LLM
3. Merge topics into dual-mode documents
4. Generate Gemini embeddings
5. Save to PostgreSQL database

Requirements:
- PostgreSQL with pgvector extension
- Gemini API key
- Environment variables set in .env file
"""

import asyncio
import os
from dotenv import load_dotenv
from unified_pipeline import UnifiedPipeline


async def example_single_url():
    """Example: Process a single URL"""
    print("=" * 80)
    print("EXAMPLE 1: Process Single URL")
    print("=" * 80)

    # Load environment variables
    load_dotenv()

    # Database configuration
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'crawl4ai'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres'),
        'port': int(os.getenv('DB_PORT', 5432))
    }

    # Initialize pipeline
    pipeline = UnifiedPipeline(
        db_config=db_config,
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        save_to_dify=False  # Set to True when Dify integration is ready
    )

    # Process a single URL
    url = 'https://docs.eosnetwork.com/docs/latest/quick-start/'
    result = await pipeline.process_url(url)

    # Print results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Success: {result['success']}")
    print(f"URL: {result['url']}")
    print(f"Timestamp: {result['timestamp']}")

    if result['success']:
        print("\nPipeline Steps:")
        for step, step_result in result['steps'].items():
            print(f"  {step}: {step_result}")


async def example_multiple_urls():
    """Example: Process multiple URLs in batch"""
    print("=" * 80)
    print("EXAMPLE 2: Process Multiple URLs")
    print("=" * 80)

    # Load environment variables
    load_dotenv()

    # Database configuration
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'crawl4ai'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres'),
        'port': int(os.getenv('DB_PORT', 5432))
    }

    # Initialize pipeline
    pipeline = UnifiedPipeline(
        db_config=db_config,
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        save_to_dify=False
    )

    # Process multiple URLs
    urls = [
        'https://docs.eosnetwork.com/docs/latest/quick-start/',
        'https://docs.eosnetwork.com/docs/latest/getting-started/',
        'https://docs.eosnetwork.com/docs/latest/core-concepts/'
    ]

    results = await pipeline.process_urls_batch(urls)

    # Print summary
    print("\n" + "=" * 80)
    print("BATCH RESULTS")
    print("=" * 80)

    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful

    print(f"Total URLs: {len(urls)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    print("\nDetails:")
    for i, result in enumerate(results, 1):
        status = "✅" if result['success'] else "❌"
        print(f"\n{i}. {status} {result['url']}")
        if result['success'] and 'steps' in result:
            merge_stats = result['steps'].get('merge', {})
            print(f"   Documents: {merge_stats.get('documents_count', 0)}")
            print(f"   Full-doc: {merge_stats.get('full_doc_count', 0)}")
            print(f"   Paragraph: {merge_stats.get('paragraph_count', 0)}")


async def example_with_error_handling():
    """Example: Process URL with comprehensive error handling"""
    print("=" * 80)
    print("EXAMPLE 3: Process with Error Handling")
    print("=" * 80)

    # Load environment variables
    load_dotenv()

    # Validate required environment variables
    required_vars = ['GEMINI_API_KEY', 'DB_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"❌ Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease set them in your .env file:")
        for var in missing_vars:
            print(f"  {var}=your_value_here")
        return

    # Database configuration with error handling
    try:
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'crawl4ai'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD'),
            'port': int(os.getenv('DB_PORT', 5432))
        }

        # Initialize pipeline
        pipeline = UnifiedPipeline(
            db_config=db_config,
            gemini_api_key=os.getenv('GEMINI_API_KEY'),
            save_to_dify=False
        )

        # Process URL
        url = 'https://docs.eosnetwork.com/docs/latest/quick-start/'
        print(f"\nProcessing: {url}")

        result = await pipeline.process_url(url)

        # Check result
        if result['success']:
            print("\n✅ Pipeline completed successfully!")
            merge_stats = result['steps'].get('merge', {})
            print(f"\n📊 Results:")
            print(f"   Topics extracted: {result['steps']['extraction']['topics_count']}")
            print(f"   Documents created: {merge_stats['documents_count']}")
            print(f"   Full-doc: {merge_stats['full_doc_count']}")
            print(f"   Paragraph: {merge_stats['paragraph_count']}")
        else:
            print(f"\n❌ Pipeline failed: {result.get('error', 'Unknown error')}")
            print("\nFailed at step:")
            for step, step_result in result.get('steps', {}).items():
                if not step_result.get('success', True):
                    print(f"  - {step}: {step_result}")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


async def example_custom_configuration():
    """Example: Using custom configuration"""
    print("=" * 80)
    print("EXAMPLE 4: Custom Configuration")
    print("=" * 80)

    load_dotenv()

    # Custom database configuration (e.g., Docker container)
    db_config = {
        'host': 'localhost',
        'database': 'crawl4ai',
        'user': 'postgres',
        'password': os.getenv('DB_PASSWORD', 'postgres'),
        'port': 5433  # Custom port (e.g., Docker mapped port)
    }

    print(f"\nDatabase Configuration:")
    print(f"  Host: {db_config['host']}")
    print(f"  Port: {db_config['port']}")
    print(f"  Database: {db_config['database']}")
    print(f"  User: {db_config['user']}")

    # Initialize pipeline
    pipeline = UnifiedPipeline(
        db_config=db_config,
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        save_to_dify=False
    )

    # Process URL
    url = 'https://docs.eosnetwork.com/docs/latest/quick-start/'
    result = await pipeline.process_url(url)

    if result['success']:
        print("\n✅ Successfully processed with custom configuration!")
    else:
        print(f"\n❌ Failed: {result.get('error', 'Unknown error')}")


def main_menu():
    """Interactive menu to choose example"""
    print("\n" + "=" * 80)
    print("UNIFIED PIPELINE EXAMPLES")
    print("=" * 80)
    print("\nChoose an example:")
    print("  1. Process single URL")
    print("  2. Process multiple URLs (batch)")
    print("  3. Process with error handling")
    print("  4. Custom configuration")
    print("  5. Run all examples")
    print("  0. Exit")

    choice = input("\nEnter choice (0-5): ").strip()
    return choice


async def run_all_examples():
    """Run all examples sequentially"""
    await example_single_url()
    print("\n" + "=" * 80 + "\n")

    await example_multiple_urls()
    print("\n" + "=" * 80 + "\n")

    await example_with_error_handling()
    print("\n" + "=" * 80 + "\n")

    await example_custom_configuration()


if __name__ == "__main__":
    # Interactive mode
    while True:
        choice = main_menu()

        if choice == "1":
            asyncio.run(example_single_url())
        elif choice == "2":
            asyncio.run(example_multiple_urls())
        elif choice == "3":
            asyncio.run(example_with_error_handling())
        elif choice == "4":
            asyncio.run(example_custom_configuration())
        elif choice == "5":
            asyncio.run(run_all_examples())
        elif choice == "0":
            print("\nExiting...")
            break
        else:
            print("\n❌ Invalid choice. Please try again.")

        input("\nPress Enter to continue...")
