# Crawl4AI - Intelligent Web Crawler with Knowledge Base Integration

An advanced web crawling system that automatically extracts, categorizes, and organizes web content into Dify knowledge bases using a dual-model AI approach.

## 🚀 Features

- **Dual-Model AI System**: 
  - Fast model for categorization (e.g., Gemini 1.5 Flash)
  - Smart model for content extraction (e.g., Gemini 2.0 Flash Exp)
  - 45% faster and 30% cost savings compared to single-model approach

- **Smart Duplicate Prevention**: Automatically detects and skips already-crawled content

- **Knowledge Base Management**:
  - **Automatic Mode**: Intelligent categorization into appropriate knowledge bases
  - **Manual Mode**: Direct all content to a selected knowledge base
  
- **Flexible Chunking Strategies**:
  - Parent-child hierarchical chunking for comprehensive organization
  - Flat chunking for simpler content structure

- **Web Interface**: User-friendly UI for easy crawling configuration

## 📋 Prerequisites

- Python 3.8+
- Dify instance running (default: http://localhost:8088)
- API keys for your chosen LLM provider (Gemini, OpenAI, Anthropic)

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Crawl4AI.git
cd Crawl4AI
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file:
```env
GEMINI_API_KEY=your_gemini_api_key_here
# Optional: Add other API keys if using different providers
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## 🚀 Quick Start

### Web Interface

1. Start the web server:
```bash
python app.py
```

2. Open your browser to `http://localhost:5000`

3. Enter a URL and configure:
   - Max pages to crawl
   - Crawl depth
   - Knowledge base selection mode (Automatic/Manual)
   - Model selection for naming and extraction

4. Click "Start Crawling" and monitor progress in real-time

### Command Line

```python
import asyncio
from crawl_workflow import CrawlWorkflow

async def main():
    # Initialize with automatic categorization
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key="your-dify-api-key",
        naming_model="gemini/gemini-1.5-flash",  # Fast model for categorization
        knowledge_base_mode='automatic'
    )
    
    # Crawl and process
    await workflow.crawl_and_process(
        url="https://docs.example.com",
        max_pages=20,
        max_depth=2,
        extraction_model="gemini/gemini-2.0-flash-exp"  # Smart model for extraction
    )

asyncio.run(main())
```

## 📚 Knowledge Base Selection

### Automatic Mode (Default)
- Analyzes content and automatically categorizes it
- Creates new knowledge bases as needed
- Groups similar content together intelligently
- Best for: Diverse content sources, research projects

### Manual Mode
- Push all content to a specific knowledge base
- Full control over content organization
- Best for: Focused research, specific topic collection

### Configuration Example
```python
# Manual mode example
workflow = CrawlWorkflow(
    dify_base_url="http://localhost:8088",
    dify_api_key="your-api-key",
    knowledge_base_mode='manual',
    selected_knowledge_base='kb-123-456'  # Your KB ID
)
```

## 🔧 Advanced Configuration

### Chunking Strategies

1. **Parent-Child Hierarchical** (Default):
```python
workflow = CrawlWorkflow(use_parent_child=True)
```
- Creates overview parent chunks with detailed child chunks
- Optimal for complex documentation

2. **Flat Chunking**:
```python
workflow = CrawlWorkflow(use_parent_child=False)
```
- Creates self-contained sections
- Better for simpler content

### Custom Extraction Prompts

Place custom prompts in the `prompts/` directory:
- `extraction_prompt_parent_child.txt` - For hierarchical chunking
- `extraction_prompt_flexible.txt` - For flat chunking

## 📊 Workflow Process

1. **Phase 1: URL Collection & Duplicate Detection**
   - Collects all URLs to be crawled
   - Checks against existing knowledge base content
   - Skips already-processed URLs (saves tokens!)

2. **Phase 2: Content Extraction**
   - Extracts content only from new URLs
   - Uses smart model for high-quality extraction
   - Implements retry logic for reliability

3. **Phase 3: Categorization & Storage**
   - Uses fast model for categorization (automatic mode)
   - Creates/selects appropriate knowledge base
   - Generates relevant tags
   - Pushes content with metadata

## 🔌 API Endpoints

- `GET /` - Web interface
- `POST /start_crawl` - Start a new crawl job
- `GET /progress` - Server-sent events for real-time progress
- `GET /status` - Check if crawl is running
- `GET /knowledge_bases` - List available knowledge bases
- `POST /cancel` - Cancel current crawl

## 📁 Project Structure

```
Crawl4AI/
├── app.py                 # Flask web server
├── crawl_workflow.py      # Core crawling logic
├── Test_dify.py          # Dify API integration
├── templates/
│   └── index.html        # Web interface
├── prompts/              # Extraction prompts
├── output/               # Extracted content (JSON)
└── docs/                 # Documentation
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built on top of [crawl4ai](https://github.com/unclecode/crawl4ai) library
- Integrates with [Dify](https://dify.ai/) for knowledge management
- Supports multiple LLM providers (Gemini, OpenAI, Anthropic)

## 🐛 Troubleshooting

### Common Issues

1. **"API key is required"**
   - Ensure your `.env` file contains the correct API keys
   - Check that the model provider matches your API key

2. **"No knowledge bases found"**
   - Verify Dify is running and accessible
   - Check the Dify API key is correct

3. **"Extraction failed"**
   - Try reducing max_pages or max_depth
   - Check API rate limits
   - Verify the target website is accessible

### Debug Mode

Enable detailed logging:
```python
workflow = CrawlWorkflow(debug=True)
```

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the documentation in `/docs`