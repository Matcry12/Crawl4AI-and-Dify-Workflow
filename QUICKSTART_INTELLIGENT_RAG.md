# Quick Start: Intelligent RAG Mode

Get started with intelligent content processing in 5 minutes!

## 1. Basic Setup

```bash
# Install dependencies
pip install crawl4ai python-dotenv tiktoken

# Set environment variables
export DIFY_API_KEY="your-dify-api-key"
export GEMINI_API_KEY="your-gemini-api-key"
```

## 2. Choose Your Mode

### Option A: Simple Word Count (Default)
```python
from crawl_workflow import CrawlWorkflow

workflow = CrawlWorkflow(
    dify_api_key="your-key",
    gemini_api_key="your-key",
    word_threshold=4000  # Switch at 4000 words
)
```

### Option B: Intelligent AI Mode
```python
workflow = CrawlWorkflow(
    dify_api_key="your-key",
    gemini_api_key="your-key",
    use_intelligent_mode=True  # AI decides everything!
)
```

## 3. Run It!

```python
import asyncio

async def main():
    await workflow.crawl_and_process(
        url="https://docs.example.com",
        max_pages=10
    )

asyncio.run(main())
```

## 4. What Happens?

### With Word Count Mode:
- ≤ 4000 words → Full doc (returns entire document)
- > 4000 words → Paragraph mode (returns chunks)

### With Intelligent Mode:
- AI analyzes content type
- Skips login pages, ads, navigation
- Single topic → Full doc
- Multi-topic → Paragraph mode

## 5. See It In Action

```bash
# Run the example
python tests/example_intelligent_mode.py
```

## That's It! 🎉

For more details, see [TUTORIAL_INTELLIGENT_RAG.md](TUTORIAL_INTELLIGENT_RAG.md)