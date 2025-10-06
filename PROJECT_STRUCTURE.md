# 📁 Crawl4AI Project Structure

## Overview
This document describes the organized folder structure of Crawl4AI - an intelligent web crawling and knowledge base management system with Dify integration.

---

## 📂 Directory Structure

```
Crawl4AI/
├── main.py                    # 🚀 Main entry point - start the application
├── requirements.txt           # 📦 Python dependencies
├── .env.example              # 🔐 Environment variables template
│
├── core/                     # 🧠 Core Business Logic
│   ├── crawl_workflow.py     # Main crawling workflow orchestration
│   ├── content_processor.py  # Content analysis and mode selection
│   ├── mode_selector.py      # Dual-mode RAG processing logic
│   ├── intelligent_content_analyzer.py  # AI-powered content analysis
│   └── resilience_utils.py   # Error recovery, retry, circuit breaker
│
├── api/                      # 🔌 External API Integrations
│   ├── dify_api_resilient.py # Dify API client with resilience features
│   ├── knowledge_base_manager.py  # KB creation and management
│   ├── document_manager.py   # Document CRUD operations
│   └── metadata_manager.py   # Metadata field management
│
├── ui/                       # 🎨 User Interface
│   ├── app.py               # Flask web server
│   └── templates/           # HTML templates
│       └── index.html       # Main UI dashboard
│
├── utils/                    # 🛠️ Utility Functions
│   ├── workflow_config.py   # Configuration management
│   └── workflow_utils.py    # Helper functions
│
├── tests/                    # 🧪 Test Suite
│   ├── test_crawl_workflow.py  # Comprehensive 10-test suite
│   ├── quick_test.py        # Fast smoke tests (< 10 sec)
│   ├── test_metadata.py     # Metadata functionality tests
│   ├── test_single_crawl.py # Single page crawl tests
│   └── [other test files]   # Legacy/specialized tests
│
├── docs/                     # 📚 Documentation
│   ├── README.md            # Main project documentation
│   ├── TEST_DOCUMENTATION.md  # Test suite guide
│   ├── DEPLOYMENT_GUIDE.md  # Deployment instructions
│   ├── INTEGRATION_SUMMARY.md  # Integration overview
│   ├── ERROR_RESILIENCE_IMPLEMENTATION_REPORT.md
│   ├── INTELLIGENT_DUAL_MODE_RAG_TUTORIAL.md
│   ├── UI_INTELLIGENT_MODE_GUIDE.md
│   └── [other docs]         # Feature-specific guides
│
├── models/                   # 📊 Data Models & Schemas
│   └── schemas.py           # Pydantic schemas for extraction
│
├── prompts/                  # 💬 LLM Prompts
│   └── [prompt templates]   # Extraction and analysis prompts
│
├── output/                   # 📤 Output Files
│   ├── test_results.json    # Test execution results
│   ├── crawl_checkpoint.json # Checkpoint for crash recovery
│   └── failure_queue.json   # Failed URL tracking
│
├── scripts/                  # 📜 Utility Scripts
│   └── setup.sh             # Installation & setup script
│
└── backup_old/              # 🗄️ Deprecated Files
    ├── crawl_orchestrator.py  # Old orchestration logic
    └── workflow_refactored_example.py

```

---

## 🚀 Quick Start

### 1. Start the Application
```bash
python main.py
```
Access UI at: http://localhost:5000

### 2. Run Tests
```bash
# Comprehensive test suite (10 tests, ~3-5 min)
python tests/test_crawl_workflow.py

# Quick smoke test (< 10 sec)
python tests/quick_test.py
```

### 3. UI Test Buttons
- **🚀 Quick Test** - Validates core functionality
- **⚡ Stress Test** - Runs full test suite via UI

---

## 📦 Key Components

### Core Workflow (`core/crawl_workflow.py`)
- **Purpose**: Main orchestration logic
- **Features**:
  - Intelligent crawling with duplicate detection
  - Automatic KB categorization
  - Dual-mode RAG processing
  - Error resilience & recovery
- **Imports**: Uses api/ and core/ modules

### Resilience System (`core/resilience_utils.py`)
- **CrawlCheckpoint**: Save/resume crawl state
- **FailureQueue**: Track failed URLs for retry
- **RetryConfig**: Exponential backoff retry logic
- **CircuitBreaker**: Prevent cascade failures

### Content Processor (`core/content_processor.py`)
- **ProcessingMode**: FULL_DOC vs PARAGRAPH
- **Dual-Mode Selection**: Word count or AI-based
- **Token Counting**: Efficient content analysis

### Dify API Client (`api/dify_api_resilient.py`)
- **Features**:
  - Automatic retry with exponential backoff
  - Circuit breaker pattern
  - KB/Document/Metadata operations
  - Parent-child chunking support

### Web UI (`ui/app.py`)
- **Flask Server**: Port 5000
- **Features**:
  - Real-time progress streaming (SSE)
  - Dual-model configuration
  - Knowledge base selection
  - Test execution via UI

---

## 🔄 Import Patterns

All modules use relative imports from project root:

```python
# In core/crawl_workflow.py
from api.dify_api_resilient import ResilientDifyAPI
from core.content_processor import ContentProcessor

# In ui/app.py
from core.crawl_workflow import CrawlWorkflow

# In tests/test_crawl_workflow.py
from core.crawl_workflow import CrawlWorkflow
from core.resilience_utils import CrawlCheckpoint
```

---

## 🧪 Test Suite

### Comprehensive Tests (`tests/test_crawl_workflow.py`)
10 tests covering:
1. ✅ Initialization
2. ✅ KB Creation
3. ✅ Document Naming
4. ✅ Duplicate Detection
5. ✅ Checkpoint System
6. ✅ Failure Queue
7. ✅ Single Page Crawl
8. ✅ Dual-Mode Selection
9. ✅ Metadata Fields
10. ✅ Category Normalization

**Success Rate**: 100% (10/10 passing)

### Quick Test (`tests/quick_test.py`)
Fast validation (< 10 seconds) for:
- Initialization
- Document naming
- Category normalization
- Checkpoint system
- Failure queue

---

## 🎯 Default AI Models

All models default to **Gemini 2.5 Flash Lite** (`gemini/gemini-2.5-flash-lite`):

- **Extraction Model**: Content processing & extraction
- **Naming Model**: KB categorization
- **Analysis Model**: Intelligent content analysis

---

## 📝 Configuration

### Environment Variables (`.env`)
```bash
DIFY_BASE_URL=http://localhost:8088
DIFY_API_KEY=your_dify_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### Key Parameters
- `max_pages`: Maximum pages to crawl
- `max_depth`: Crawl depth limit
- `word_threshold`: Dual-mode switching threshold (default: 4000)
- `enable_dual_mode`: Enable smart mode selection
- `enable_resilience`: Enable retry & recovery

---

## 🗑️ Deprecated Files

Files in `backup_old/` are kept for reference but not used:
- `crawl_orchestrator.py` - Old orchestration logic
- `workflow_refactored_example.py` - Example code

---

## 📊 Output Files

### Test Results (`output/test_results.json`)
```json
{
  "timestamp": 23556.792276022,
  "total": 10,
  "passed": 10,
  "failed": 0,
  "results": [...]
}
```

### Checkpoint (`output/crawl_checkpoint.json`)
- Tracks crawl progress
- Enables resume after crash
- Stores processed/pending URLs

### Failure Queue (`output/failure_queue.json`)
- Failed URLs with error messages
- Retry count tracking
- Exportable report

---

## 🔗 Dependencies

See `requirements.txt` for full list. Key dependencies:
- `crawl4ai` - Web crawling framework
- `flask` - Web UI server
- `python-dotenv` - Environment management
- `requests` - HTTP client
- `pydantic` - Data validation

---

## 📞 Support

- **Documentation**: See `docs/` folder
- **Issues**: GitHub issues
- **Tests**: Run test suite for validation

---

**Last Updated**: 2025-10-06
**Project Version**: 2.0 (Restructured)
**Test Coverage**: 100% (10/10 tests passing)
