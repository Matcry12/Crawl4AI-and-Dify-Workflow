#!/usr/bin/env python3
"""
Clear Database - Simple script to clear all data from PostgreSQL

Removes all documents, chunks, and merge history from the database.
"""

import os
import sys
import subprocess

# Database configuration
POSTGRES_CONTAINER = os.getenv('POSTGRES_CONTAINER', 'postgres-crawl4ai')
POSTGRES_DATABASE = os.getenv('POSTGRES_DATABASE', 'crawl4ai')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')


def clear_database():
    """Clear all data from the database"""
    print("=" * 80)
    print("🗑️   DATABASE CLEANER")
    print("=" * 80)
    print(f"Container: {POSTGRES_CONTAINER}")
    print(f"Database:  {POSTGRES_DATABASE}")
    print("=" * 80)
    print()

    # Ask for confirmation
    response = input("⚠️  This will DELETE ALL data. Are you sure? (yes/no): ").strip().lower()

    if response != 'yes':
        print("\n❌ Cancelled. No data was deleted.")
        return

    print("\n🔄 Clearing database...")

    try:
        # Execute TRUNCATE command
        cmd = [
            'docker', 'exec', '-i', POSTGRES_CONTAINER,
            'psql', '-U', POSTGRES_USER, '-d', POSTGRES_DATABASE,
            '-c', 'TRUNCATE TABLE chunks, merge_history, documents CASCADE;'
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        print("✅ Database cleared successfully!")
        print()
        print("=" * 80)
        print("📊 VERIFICATION")
        print("=" * 80)

        # Verify counts
        count_cmd = [
            'docker', 'exec', '-i', POSTGRES_CONTAINER,
            'psql', '-U', POSTGRES_USER, '-d', POSTGRES_DATABASE,
            '-t', '-A',
            '-c', 'SELECT COUNT(*) FROM documents;'
        ]

        count_result = subprocess.run(
            count_cmd,
            capture_output=True,
            text=True,
            check=True
        )

        doc_count = count_result.stdout.strip()
        print(f"Documents: {doc_count}")

        if doc_count == '0':
            print("✅ All data successfully removed!")
        else:
            print(f"⚠️  Warning: {doc_count} documents still remain")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error clearing database: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

    print("=" * 80)


if __name__ == "__main__":
    clear_database()
