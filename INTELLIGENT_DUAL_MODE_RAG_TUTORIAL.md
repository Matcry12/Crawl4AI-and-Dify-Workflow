# Intelligent Dual-Mode RAG Tutorial

## Table of Contents
1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Installation & Setup](#installation--setup)
4. [Mode Selection Strategies](#mode-selection-strategies)
5. [Using the UI](#using-the-ui)
6. [Programmatic Usage](#programmatic-usage)
7. [Understanding the Results](#understanding-the-results)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

The Intelligent Dual-Mode RAG system automatically optimizes how content is processed for Retrieval-Augmented Generation (RAG) based on content structure. It solves a key RAG challenge: should content be chunked (paragraph mode) or kept whole (full doc mode)?

### Why Dual-Mode?

- **Full Doc Mode**: Returns entire documents when any chunk matches
  - Best for: Single-topic content (tutorials, guides, profiles)
  - Example: A Python tutorial should return the complete tutorial, not just the matching section

- **Paragraph Mode**: Returns only matching chunks
  - Best for: Multi-topic content (mixed subjects, reference lists)
  - Example: A page about "History of Rome AND History of Greece" should return only the relevant civilization

## Core Concepts

### 1. Processing Modes

| Mode | Returns | Best For | Example |
|------|---------|----------|---------|
| **Full Doc** | Entire document | Single coherent topic | Complete Python tutorial |
| **Paragraph** | Matching chunks only | Multiple distinct topics | Blog with diverse posts |

### 2. Mode Selection Strategies

| Strategy | How it Works | When to Use |
|----------|--------------|-------------|
| **Threshold-Based** | Uses word count (4000 default) | Simple, fast, predictable |
| **AI-Powered** | LLM analyzes content structure | Intelligent, context-aware |
| **Manual** | You choose the mode | Testing, special cases |

### 3. Content Analysis (AI-Powered Mode)

The system evaluates:
- **Content Value**: High/Medium/Low/Skip
- **Structure**: Single-topic/Multi-topic/Reference/List
- **Filtering**: Automatically skips login pages, ads, navigation

## Installation & Setup

### Prerequisites

```bash
# Clone the repository
git clone https://github.com/your-repo/Crawl4AI.git
cd Crawl4AI

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key  # Optional
ANTHROPIC_API_KEY=your-anthropic-key  # Optional
EOF
```

### Starting the UI

```bash
python app.py
```

Navigate to `http://localhost:5000`

## Mode Selection Strategies

### 1. Threshold-Based (Simple)

```yaml
Strategy: Word Count Threshold
Settings:
  - Word Threshold: 4000 words
  - Logic: < 4000 words → Full Doc
          ≥ 4000 words → Paragraph
```

**Use When:**
- Content length correlates with complexity
- Need predictable behavior
- Testing initial setup

### 2. AI-Powered Analysis (Intelligent)

```yaml
Strategy: AI-Powered Analysis
Model: gemini/gemini-1.5-flash (default)
Analysis:
  - Content Value: Filters low-value pages
  - Structure: Detects single vs multi-topic
  - Smart Mode Selection
```

**Use When:**
- Content varies widely
- Need intelligent filtering
- Want optimal RAG performance

### 3. Manual Selection

```yaml
Strategy: Manual Mode Selection
Options:
  - Force Full Doc Mode
  - Force Paragraph Mode
```

**Use When:**
- Testing specific modes
- Know content structure
- Debugging issues

## Using the UI

### Basic Crawl Setup

1. **Enter URL**: The starting point for crawling
2. **Max Pages**: Limit pages to crawl (default: 10)
3. **Max Depth**: How deep to follow links (0 = current page only)

### Model Configuration

```yaml
Extraction Model: gemini/gemini-2.0-flash-exp  # Main content processing
Naming Model: gemini/gemini-1.5-flash          # Fast categorization
```

### RAG Optimization Settings

1. **Enable Dual-Mode RAG**: ✅ (Check to enable)

2. **Mode Selection Strategy**:
   ```yaml
   📏 Word Count Threshold (4000 words)
   🤖 AI-Powered Analysis
   ✋ Manual: Full Doc Mode
   ✋ Manual: Paragraph Mode
   ```

3. **For AI-Powered Analysis**:
   ```yaml
   Content Analysis Model: [gemini/gemini-1.5-flash ▼]
   # Or select "➕ Custom Model..." for custom LLM
   ```

### Custom LLM Support

```yaml
Advanced Settings:
  ☑ Use Custom LLM Provider
    Base URL: https://your-llm.com/v1
    API Key: your-key

Then in dropdowns:
  Extraction Model: ➕ Custom Model... → your-model-name
  Analysis Model: ➕ Custom Model... → your-analysis-model
```

## Programmatic Usage

### Basic Example

```python
from crawl_workflow import CrawlWorkflow

# Initialize with intelligent mode
workflow = CrawlWorkflow(
    gemini_api_key="your-key",
    enable_dual_mode=True,
    use_intelligent_mode=True
)

# Crawl and process
await workflow.crawl_and_process(
    url="https://docs.python.org/tutorial",
    max_pages=10,
    extraction_model="gemini/gemini-2.0-flash-exp"
)
```

### Advanced Configuration

```python
# Custom analysis model
workflow = CrawlWorkflow(
    gemini_api_key="your-key",
    enable_dual_mode=True,
    use_intelligent_mode=True,
    intelligent_analysis_model="openai/gpt-4",
    word_threshold=3000,  # Custom threshold as fallback
    custom_llm_base_url="https://your-llm.com/v1",
    custom_llm_api_key="your-custom-key"
)

# Manual mode override
workflow = CrawlWorkflow(
    enable_dual_mode=True,
    manual_mode="full_doc"  # Force full doc mode
)
```

### Accessing Analysis Results

```python
# The workflow logs detailed analysis
🔍 Analyzing content structure...
📊 Content Analysis Results:
  - Value: high (Comprehensive Python tutorial)
  - Structure: single_topic (Focused on Python basics)
  - Topics: ['Python programming', 'syntax', 'data types']
  - Mode: full_doc (Single coherent topic needs full context)
  ✅ Page will be processed
```

## Understanding the Results

### Progress Logs

```bash
🧠 Model Configuration:
  📝 Naming: gemini/gemini-1.5-flash (fast categorization)
  🔍 Extraction: gemini/gemini-2.0-flash-exp (smart content processing)

🔀 Dual-Mode RAG: ENABLED
  🤖 Using AI-powered content analysis
  📊 Analysis model: gemini/gemini-1.5-flash

🌐 Starting crawl from: https://example.com
📄 Processing page 1/10: https://example.com/tutorial

🔍 Analyzing content structure...
📊 Content Analysis Results:
  - Value: high (Comprehensive tutorial content)
  - Structure: single_topic (Unified Python tutorial)
  - Mode: full_doc (Complete context needed)
  ✅ Page will be processed

🔄 Switching to FULL DOC mode for optimal RAG
📝 Using extraction prompt: prompts/extraction_prompt_full_doc.txt
```

### Mode Selection Examples

#### Example 1: Tutorial (Full Doc)
```yaml
URL: https://site.com/python-tutorial
Analysis:
  - 50 pages of Python content
  - All about one topic: Python
  - Mode: full_doc ✓
  - Reason: Single coherent topic
```

#### Example 2: Blog (Paragraph)
```yaml
URL: https://site.com/tech-blog
Analysis:
  - Mixed content: AI, Cooking, Travel
  - Multiple unrelated topics
  - Mode: paragraph ✓
  - Reason: Users need specific chunks
```

#### Example 3: Navigation (Skip)
```yaml
URL: https://site.com/sitemap
Analysis:
  - Value: low
  - Type: Pure navigation
  - Action: SKIPPED ❌
  - Reason: No valuable content
```

## Best Practices

### 1. Model Selection

```yaml
Extraction Model:
  - High-quality: gemini-2.0-flash-exp, gpt-4
  - Fast: gemini-1.5-flash, gpt-3.5-turbo

Analysis Model:
  - Recommended: gemini-1.5-flash (fast & cheap)
  - High-accuracy: gpt-4 (if needed)

Naming Model:
  - Always use fast model: gemini-1.5-flash
```

### 2. When to Use Each Strategy

| Content Type | Recommended Strategy | Why |
|--------------|---------------------|-----|
| Documentation | AI-Powered | Varies between API refs and guides |
| Tutorials | Manual (Full Doc) | Always single-topic |
| News Sites | AI-Powered | Mixed content types |
| Blogs | Threshold or AI | Depends on blog style |
| E-commerce | AI-Powered | Filter product pages |

### 3. Performance Tips

1. **Start Small**: Test with max_pages=5 first
2. **Use Caching**: Rerun without re-crawling
3. **Monitor Logs**: Check mode selection reasons
4. **Adjust Threshold**: Based on your content

## Troubleshooting

### Issue: Wrong Mode Selected

```yaml
Symptom: Tutorial split into chunks
Solution:
  1. Check analysis results in logs
  2. Try manual mode to test
  3. Adjust word threshold
  4. Use different analysis model
```

### Issue: Low-Value Pages Processed

```yaml
Symptom: Login pages in knowledge base
Solution:
  1. Enable AI-Powered Analysis
  2. Check content value in logs
  3. Verify analysis model is working
```

### Issue: Slow Processing

```yaml
Symptom: Takes too long
Solution:
  1. Use faster analysis model
  2. Reduce max_pages
  3. Enable caching
  4. Use threshold mode for speed
```

### Issue: Custom Model Not Working

```yaml
Symptom: Custom LLM errors
Solution:
  1. Verify OpenAI-compatible API
  2. Check endpoint URL format
  3. Test with simple prompt first
  4. Check API key permissions
```

## Advanced Topics

### Content Analysis Internals

The AI analyzer evaluates:

```python
{
    "content_value": "high|medium|low|skip",
    "content_structure": "single_topic|multi_topic|reference|list",
    "main_topics": ["topic1", "topic2"],
    "recommended_mode": "full_doc|paragraph",
    "has_code": true|false,
    "is_navigational": true|false
}
```

### Custom Analysis Prompts

Located in `intelligent_content_analyzer.py:_create_analysis_prompt()`

Key rules:
- Length does NOT determine mode
- Topic unity is key factor
- Full doc returns entire document
- Paragraph returns only chunks

### Integration with Dify

The system automatically:
1. Creates/updates knowledge bases
2. Uploads documents with proper mode
3. Handles both hierarchical (paragraph) and text (full doc) models

## Summary

The Intelligent Dual-Mode RAG system provides:

1. **Automatic Optimization**: Content-aware processing
2. **Flexible Strategies**: Threshold, AI, or Manual
3. **Smart Filtering**: Skip low-value content
4. **Custom Model Support**: Use any OpenAI-compatible LLM
5. **Full Integration**: Works with existing Crawl4AI features

Start with AI-Powered Analysis for best results, then optimize based on your specific content and needs!