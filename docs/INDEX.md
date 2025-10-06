# 📚 Documentation Index

Complete guide to Crawl4AI documentation.

---

## 🚀 Getting Started

| Document | Description |
|----------|-------------|
| [README.md](../README.md) | **Main project overview** ⭐ Start here! |
| [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) | **Folder organization guide** 📂 |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Setup and deployment instructions |

---

## 🧪 Testing

| Document | Description |
|----------|-------------|
| [TEST_DOCUMENTATION.md](TEST_DOCUMENTATION.md) | **Complete test suite guide** |

### Test Files

Located in `tests/` folder:

- **`test_crawl_workflow.py`** - Comprehensive 10-test suite
  - Initialization, KB creation, duplicate detection
  - Checkpoint system, failure queue
  - Dual-mode selection, metadata fields
  - Category normalization, single page crawl
  - **Success Rate: 100% (10/10 passing)**

- **`quick_test.py`** - Fast smoke tests (< 10 seconds)
  - Core functionality validation
  - Quick feedback during development

- **`Test_dify.py`** - Dify API client class
  - Used by UI application
  - KB and document operations

---

## 🎨 User Interface

| Document | Description |
|----------|-------------|
| [README_UI.md](README_UI.md) | **Web UI complete guide** |
| [UI_INTELLIGENT_MODE_GUIDE.md](UI_INTELLIGENT_MODE_GUIDE.md) | Intelligent mode tutorial |

### UI Features

- Real-time progress streaming
- Dual-model configuration (Gemini 2.5 Flash Lite default)
- Knowledge base selection (Automatic/Manual)
- **🚀 Quick Test** button (< 10 sec)
- **⚡ Stress Test** button (3-5 min, runs full suite)

---

## 🧠 Features & Architecture

| Document | Description |
|----------|-------------|
| [ERROR_RESILIENCE_IMPLEMENTATION_REPORT.md](ERROR_RESILIENCE_IMPLEMENTATION_REPORT.md) | **Error resilience system** - Retry logic, circuit breaker, checkpoints |
| [INTELLIGENT_DUAL_MODE_RAG_TUTORIAL.md](INTELLIGENT_DUAL_MODE_RAG_TUTORIAL.md) | **Dual-mode RAG system** - Full doc vs paragraph mode |
| [KB_API.md](KB_API.md) | **Knowledge base API reference** |

### Key Features

**Error Resilience:**
- Exponential backoff retry logic
- Circuit breaker pattern
- Checkpoint/resume system
- Failure queue with retry tracking

**Dual-Mode RAG:**
- Full Document Mode (sections) - for focused content
- Paragraph Mode (parent-child) - for multi-topic content
- Automatic or AI-powered mode selection
- Smart content analysis

**Processing:**
- Duplicate detection and prevention
- Automatic KB categorization
- Parent-child hierarchical chunking
- Metadata field management

---

## 📖 API Reference

| Document | Description |
|----------|-------------|
| [KB_API.md](KB_API.md) | Knowledge base API operations |

**Available Operations:**
- Create/delete knowledge bases
- Create/update/delete documents
- Manage metadata fields
- Retrieve documents
- Handle tags and bindings

---

## 🔍 Quick Navigation

### For New Users:
1. Start with [README.md](../README.md)
2. Understand the structure: [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md)
3. Deploy the project: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
4. Use the UI: [README_UI.md](README_UI.md)

### For Developers:
1. Run tests: [TEST_DOCUMENTATION.md](TEST_DOCUMENTATION.md)
2. Understand resilience: [ERROR_RESILIENCE_IMPLEMENTATION_REPORT.md](ERROR_RESILIENCE_IMPLEMENTATION_REPORT.md)
3. Learn dual-mode RAG: [INTELLIGENT_DUAL_MODE_RAG_TUTORIAL.md](INTELLIGENT_DUAL_MODE_RAG_TUTORIAL.md)
4. API reference: [KB_API.md](KB_API.md)

### For Power Users:
1. Intelligent mode guide: [UI_INTELLIGENT_MODE_GUIDE.md](UI_INTELLIGENT_MODE_GUIDE.md)
2. Dual-mode RAG tutorial: [INTELLIGENT_DUAL_MODE_RAG_TUTORIAL.md](INTELLIGENT_DUAL_MODE_RAG_TUTORIAL.md)
3. API operations: [KB_API.md](KB_API.md)

---

## 📂 Documentation Structure

```
docs/
├── INDEX.md (this file)           # Documentation navigation
├── README_UI.md                   # Web interface guide
├── DEPLOYMENT_GUIDE.md            # Setup instructions
├── TEST_DOCUMENTATION.md          # Testing guide
├── ERROR_RESILIENCE_IMPLEMENTATION_REPORT.md  # Resilience features
├── INTELLIGENT_DUAL_MODE_RAG_TUTORIAL.md      # RAG system
├── UI_INTELLIGENT_MODE_GUIDE.md   # Advanced UI features
└── KB_API.md                      # API reference
```

---

## 🎯 Default Configuration

**AI Models (all default to Gemini 2.5 Flash Lite):**
- Extraction Model: `gemini/gemini-2.5-flash-lite`
- Naming Model: `gemini/gemini-2.5-flash-lite`
- Analysis Model: `gemini/gemini-2.5-flash-lite`

**Processing:**
- Word Threshold: 4000 words
- Enable Dual Mode: True
- Enable Resilience: True
- Knowledge Base Mode: Automatic

---

## 📊 Test Coverage

**Comprehensive Test Suite (`test_crawl_workflow.py`):**

| Test | Status | Description |
|------|--------|-------------|
| 1. Initialization | ✅ PASS | All components initialize correctly |
| 2. KB Creation | ✅ PASS | Knowledge base creation and caching |
| 3. Document Naming | ✅ PASS | Consistent document name generation |
| 4. Duplicate Detection | ✅ PASS | URL duplicate checking |
| 5. Checkpoint System | ✅ PASS | Save/load functionality |
| 6. Failure Queue | ✅ PASS | Failed URL tracking and retry |
| 7. Single Page Crawl | ✅ PASS | End-to-end real crawl |
| 8. Dual-Mode Selection | ✅ PASS | Mode selection logic |
| 9. Metadata Fields | ✅ PASS | Metadata field creation |
| 10. Category Normalization | ✅ PASS | Category name standardization |

**Success Rate: 100% (10/10 tests passing)**

---

## 🚀 Running the Application

```bash
# Start web UI
python main.py

# Access at: http://localhost:5000

# Run tests
python tests/test_crawl_workflow.py    # Comprehensive (3-5 min)
python tests/quick_test.py              # Quick (< 10 sec)
```

---

**Last Updated**: 2025-10-06
**Documentation Version**: 2.0 (Cleaned & Reorganized)
**Total Documents**: 8 essential guides
