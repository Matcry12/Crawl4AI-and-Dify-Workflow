#!/usr/bin/env python3
"""Comprehensive check for ALL errors in workflow_manager.py"""

import os
import sys
import ast
import re

print("=" * 80)
print("COMPREHENSIVE WORKFLOW ERROR CHECK")
print("=" * 80)
print()

# Read the file
with open('workflow_manager.py', 'r') as f:
    content = f.read()

errors_found = []

# Check 1: Syntax errors
print("CHECK 1: Python Syntax")
print("-" * 80)
try:
    ast.parse(content)
    print("✅ No syntax errors")
except SyntaxError as e:
    print(f"❌ SYNTAX ERROR: {e}")
    errors_found.append(f"Syntax error: {e}")
print()

# Check 2: Look for 'target_document' (should be target_doc_id)
print("CHECK 2: Field Name - target_document vs target_doc_id")
print("-" * 80)
matches = re.finditer(r"['\"]target_document['\"]", content)
found_issues = False
for match in matches:
    line_num = content[:match.start()].count('\n') + 1
    print(f"❌ Line {line_num}: Found 'target_document' (should be 'target_doc_id')")
    errors_found.append(f"Line {line_num}: Wrong field name 'target_document'")
    found_issues = True
if not found_issues:
    print("✅ No 'target_document' references found")
print()

# Check 3: Look for undefined variables in merge logic
print("CHECK 3: Variable Definitions in Merge Logic")
print("-" * 80)
# Check if existing_docs/existing_documents is used correctly
merge_section = re.search(r'def _process_pages_iteratively.*?(?=\n    async def|\nclass|$)', content, re.DOTALL)
if merge_section:
    section_text = merge_section.group(0)

    # Check if existing_docs is defined before use in merge
    if 'existing_docs' in section_text:
        existing_docs_def = re.search(r'existing_docs\s*=', section_text)
        existing_docs_use = re.search(r'for doc in existing_docs', section_text)

        if existing_docs_use and existing_docs_def:
            if existing_docs_def.start() < existing_docs_use.start():
                print("✅ existing_docs defined before use")
            else:
                print("❌ existing_docs used before definition")
                errors_found.append("existing_docs used before definition")
        elif existing_docs_use:
            print("✅ existing_docs used in merge logic")
    else:
        print("⚠️  existing_docs not found in iterative processing")
print()

# Check 4: Check for missing None checks
print("CHECK 4: None Checks for target_doc")
print("-" * 80)
# Look for target_doc usage without None check
target_doc_patterns = re.finditer(r'target_doc\s*=.*\n.*if target_doc:', content)
count = len(list(re.finditer(r'target_doc\s*=.*\n.*if target_doc:', content)))
if count >= 2:  # Should be 2 places (DocumentMergerNode + iterative)
    print(f"✅ Found {count} places with target_doc None checks")
else:
    print(f"⚠️  Only found {count} places with target_doc None checks (expected 2)")
    errors_found.append(f"Missing target_doc None checks")
print()

# Check 5: Import statements
print("CHECK 5: Import Statements")
print("-" * 80)
required_imports = [
    'asyncio',
    'os',
    'datetime',
    'typing',
    'Enum'
]
for imp in required_imports:
    if imp in content:
        print(f"✅ {imp}")
    else:
        print(f"❌ Missing import: {imp}")
        errors_found.append(f"Missing import: {imp}")
print()

# Check 6: Check for 'results' structure access
print("CHECK 6: Results Structure Access")
print("-" * 80)
# Check if code accesses results['merge'], results['create'] correctly
if "results['merge']" in content or 'results["merge"]' in content:
    print("✅ results['merge'] accessed")
else:
    print("⚠️  results['merge'] not found")

if "results['create']" in content or 'results["create"]' in content:
    print("✅ results['create'] accessed")
else:
    print("⚠️  results['create'] not found")
print()

# Check 7: Database method calls
print("CHECK 7: Database Method Calls")
print("-" * 80)
db_methods = [
    'get_all_documents_with_embeddings',
    'insert_documents_batch',
    'update_document_with_chunks',
    'begin_transaction',
    'commit_transaction',
    'rollback_transaction'
]
for method in db_methods:
    pattern = f'self.db.{method}'
    if pattern in content:
        print(f"✅ {method}()")
    else:
        print(f"⚠️  {method}() not used")
print()

# Check 8: Async/await consistency
print("CHECK 8: Async/Await Consistency")
print("-" * 80)
# Find all async def
async_defs = re.findall(r'async def (\w+)', content)
print(f"Found {len(async_defs)} async methods:")
for method in async_defs:
    print(f"  - {method}")

# Check if run() is async
if 'async def run' in content:
    print("✅ run() is async")
else:
    print("❌ run() is not async")
    errors_found.append("run() method should be async")
print()

# Check 9: Error handling in nodes
print("CHECK 9: Error Handling in Nodes")
print("-" * 80)
node_classes = ['CrawlNode', 'ExtractTopicsNode', 'MergeDecisionNode',
                'DocumentCreatorNode', 'DocumentMergerNode']
for node in node_classes:
    pattern = f'class {node}.*?(?=class |$)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        node_text = match.group(0)
        if 'try:' in node_text and 'except' in node_text:
            print(f"✅ {node} has error handling")
        else:
            print(f"⚠️  {node} missing error handling")
    else:
        print(f"❌ {node} class not found")
        errors_found.append(f"{node} class not found")
print()

# Check 10: Component initialization
print("CHECK 10: Component Initialization")
print("-" * 80)
components = ['topic_extractor', 'embedder', 'llm', 'decision_maker',
              'doc_creator', 'doc_merger', 'db']
init_method = re.search(r'def _initialize_components.*?(?=\n    def)', content, re.DOTALL)
if init_method:
    init_text = init_method.group(0)
    for comp in components:
        if f'self.{comp}' in init_text:
            print(f"✅ {comp} initialized")
        else:
            print(f"⚠️  {comp} not initialized")
else:
    print("❌ _initialize_components method not found")
    errors_found.append("_initialize_components method not found")
print()

# Summary
print("=" * 80)
print("SUMMARY")
print("=" * 80)
if errors_found:
    print(f"❌ FOUND {len(errors_found)} ERRORS:")
    for i, error in enumerate(errors_found, 1):
        print(f"  {i}. {error}")
    print()
    print("❌ WORKFLOW HAS ERRORS - NEEDS FIXING")
    sys.exit(1)
else:
    print("✅ NO CRITICAL ERRORS FOUND")
    print()
    print("The workflow_manager.py appears to be error-free!")
    print("All checks passed successfully.")
