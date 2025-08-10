# Parent-Child Chunking Implementation

This document explains the new parent-child chunking feature implemented in the Crawl4AI workflow.

## Overview

Parent-child chunking creates a hierarchical structure for your content, where:
- **Parent chunks** provide high-level overviews and context (500-1500 words)
- **Child chunks** contain detailed information, examples, and step-by-step instructions (200-800 words)

This approach is ideal for complex documentation, tutorials, and structured content that benefits from both overview and detailed perspectives.

## Key Features

### 1. Hierarchical Structure
```
###PARENT_SECTION###[Complete Overview]
  └── ###CHILD_SECTION###[Specific Details 1]
  └── ###CHILD_SECTION###[Specific Details 2]
  └── ###CHILD_SECTION###[Specific Details 3]

###PARENT_SECTION###[Another Major Topic]
  └── ###CHILD_SECTION###[Implementation Details]
  └── ###CHILD_SECTION###[Examples and Use Cases]
```

### 2. Flexible Configuration

Enable parent-child chunking when initializing the workflow:

```python
workflow = CrawlWorkflow(
    dify_base_url="http://localhost:8088",
    dify_api_key="your-api-key",
    gemini_api_key=os.getenv('GEMINI_API_KEY'),
    use_parent_child=True  # Enable parent-child mode
)
```

### 3. Automatic Separator Detection

The system automatically uses the appropriate separators:
- Parent chunks: `###PARENT_SECTION###`
- Child chunks: `###CHILD_SECTION###`
- Flat mode: `###SECTION_BREAK###` (when `use_parent_child=False`)

## Implementation Details

### Modified Files

1. **`prompts/extraction_prompt_parent_child.txt`**
   - New prompt specifically designed for hierarchical extraction
   - Instructs the LLM to create parent-child relationships
   - Ensures proper context distribution between levels

2. **`Test_dify.py`**
   - Updated `create_document_from_text()` method
   - Added `use_parent_child` parameter
   - Configures Dify API for hierarchical chunking:
     - Parent chunks: max 1500 tokens, 100 token overlap
     - Child chunks: max 800 tokens, 50 token overlap

3. **`crawl_workflow.py`**
   - Added `use_parent_child` parameter to constructor
   - Automatic prompt selection based on mode
   - Updated chunk counting for hierarchical structure
   - Passes configuration to Dify API

## Usage Examples

### Basic Usage

```python
# Initialize with parent-child chunking
workflow = CrawlWorkflow(
    dify_base_url="http://localhost:8088",
    dify_api_key="your-api-key",
    use_parent_child=True
)

# Process content
await workflow.crawl_and_process(
    url="https://docs.example.com",
    max_pages=10,
    max_depth=1
)
```

### Testing Parent-Child Extraction

Use the provided test script:

```bash
python test_parent_child.py
```

This will:
- Extract content from a test URL
- Display the hierarchical structure
- Show parent and child section titles
- Save sample output for inspection

### Comparing Chunking Modes

```bash
python compare_chunking_modes.py
```

This script explains the differences between flat and parent-child chunking.

## When to Use Each Mode

### Use Parent-Child Chunking for:
- Technical documentation with multiple topics
- Tutorials and step-by-step guides
- API documentation with overview and details
- Complex content requiring both summary and specifics
- Content where users might need either high-level or detailed information

### Use Flat Chunking for:
- Blog posts and articles
- Simple, linear documentation
- News content
- FAQs with independent questions
- Content without clear hierarchical structure

## Benefits

1. **Better Context Preservation**: Parent chunks maintain topic overview while children provide details
2. **Flexible Retrieval**: RAG systems can return either overviews or detailed chunks based on query
3. **Improved Organization**: Natural hierarchy matches documentation structure
4. **Redundancy by Design**: Important information appears in both parent and child for better retrieval

## Configuration in Dify

The implementation automatically configures Dify with:
- `doc_form: "hierarchical_model"` for parent-child mode
- `doc_form: "text_model"` for flat mode
- Appropriate separators and token limits for each level

## Monitoring

The system provides detailed feedback:
```
📝 Using parent-child chunking mode
📝 Description: 15234 characters in 4 parent chunks with 12 child chunks
```

## Troubleshooting

1. **Chunks too small/large**: Adjust token limits in `Test_dify.py`
2. **Missing hierarchy**: Check that the prompt file exists and is loaded correctly
3. **Separator issues**: Ensure the LLM is using the correct separators as defined in the prompt

## Future Enhancements

Consider these potential improvements:
- Three-level hierarchy support (grandparent-parent-child)
- Dynamic token limits based on content type
- Custom separator configuration
- Chunk relationship mapping in Dify