#!/usr/bin/env python3
"""
Unit tests for the ContentProcessor class
"""

from content_processor import ContentProcessor, ProcessingMode

def test_token_counting():
    """Test token counting functionality."""
    processor = ContentProcessor()
    
    # Test short text
    short_text = "This is a short test document with minimal content."
    token_count = processor.count_tokens(short_text)
    print(f"Short text tokens: {token_count}")
    
    # Test longer text
    long_text = "This is a much longer document. " * 1000  # Repeat to make it long
    token_count_long = processor.count_tokens(long_text)
    print(f"Long text tokens: {token_count_long}")
    
    return token_count < token_count_long

def test_mode_selection():
    """Test processing mode selection logic."""
    processor = ContentProcessor(token_threshold=100)  # Low threshold for testing
    
    # Test short content
    short_content = "This is short content."
    mode, analysis = processor.determine_processing_mode(short_content)
    
    print(f"\nShort content analysis:")
    print(f"  Content: '{short_content[:50]}...'")
    print(f"  Token count: {analysis['token_count']}")
    print(f"  Selected mode: {mode.value}")
    print(f"  Reason: {analysis['selection_reason']}")
    
    # Test long content
    long_content = "This is a very long piece of content. " * 50
    mode_long, analysis_long = processor.determine_processing_mode(long_content)
    
    print(f"\nLong content analysis:")
    print(f"  Content: '{long_content[:50]}...'")
    print(f"  Token count: {analysis_long['token_count']}")
    print(f"  Selected mode: {mode_long.value}")
    print(f"  Reason: {analysis_long['selection_reason']}")
    
    return mode == ProcessingMode.FULL_DOC and mode_long == ProcessingMode.PARAGRAPH

def test_url_patterns():
    """Test URL pattern detection."""
    processor = ContentProcessor()
    
    test_urls = [
        ("https://docs.example.com/api/users", True),
        ("https://example.com/faq", True),
        ("https://docs.example.com/quickstart", True),
        ("https://example.com/blog/post-123", False),
        ("https://docs.example.com/comprehensive-guide", False)
    ]
    
    print(f"\nURL Pattern Tests:")
    all_correct = True
    
    for url, expected_full_doc in test_urls:
        result = processor.should_use_full_doc_for_url(url)
        status = "✅" if result == expected_full_doc else "❌"
        print(f"  {status} {url} -> {'Full Doc' if result else 'Paragraph'}")
        
        if result != expected_full_doc:
            all_correct = False
    
    return all_correct

def test_dify_configuration():
    """Test Dify configuration generation."""
    processor = ContentProcessor()
    
    # Test paragraph mode config
    paragraph_config = processor.get_dify_configuration(ProcessingMode.PARAGRAPH)
    print(f"\nParagraph mode config:")
    print(f"  doc_form: {paragraph_config['doc_form']}")
    print(f"  mode: {paragraph_config['process_rule']['mode']}")
    print(f"  parent separator: {paragraph_config['process_rule']['rules']['segmentation']['separator']}")
    
    # Test full doc mode config
    full_doc_config = processor.get_dify_configuration(ProcessingMode.FULL_DOC)
    print(f"\nFull doc mode config:")
    print(f"  doc_form: {full_doc_config['doc_form']}")
    print(f"  mode: {full_doc_config['process_rule']['mode']}")
    print(f"  section separator: {full_doc_config['process_rule']['rules']['subchunk_segmentation']['separator']}")
    
    return (paragraph_config['doc_form'] == 'hierarchical_model' and 
            full_doc_config['doc_form'] == 'hierarchical_model')

def test_prompts():
    """Test prompt generation."""
    processor = ContentProcessor()
    
    # Test paragraph prompt
    paragraph_prompt = processor.get_extraction_prompt(ProcessingMode.PARAGRAPH)
    print(f"\nParagraph prompt (first 100 chars):")
    print(f"  {paragraph_prompt[:100]}...")
    
    # Test full doc prompt
    full_doc_prompt = processor.get_extraction_prompt(ProcessingMode.FULL_DOC)
    print(f"\nFull doc prompt (first 100 chars):")
    print(f"  {full_doc_prompt[:100]}...")
    
    return "###PARENT_SECTION###" in paragraph_prompt and "###SECTION###" in full_doc_prompt

def main():
    """Run all tests."""
    print("🧪 ContentProcessor Unit Tests")
    print("=" * 50)
    
    tests = [
        ("Token Counting", test_token_counting),
        ("Mode Selection", test_mode_selection),
        ("URL Patterns", test_url_patterns),
        ("Dify Configuration", test_dify_configuration),
        ("Prompt Generation", test_prompts)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        print("-" * 30)
        
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"\n{status}: {test_name}")
        except Exception as e:
            results.append((test_name, False))
            print(f"\n❌ ERROR in {test_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print(f"\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Dual-mode system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()