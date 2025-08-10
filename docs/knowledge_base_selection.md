# Knowledge Base Selection Feature

## Overview
This feature allows users to choose between automatic intelligent categorization or manual selection of a specific knowledge base when crawling websites.

## Usage Modes

### 1. Automatic Mode (Default)
- **How it works**: The system intelligently analyzes content and automatically categorizes it into appropriate knowledge bases
- **Benefits**: 
  - Groups similar content together
  - Creates new knowledge bases as needed
  - Uses smart duplicate prevention
  - Optimal for diverse content sources

### 2. Manual Mode
- **How it works**: All crawled content is pushed to a user-selected knowledge base
- **Benefits**:
  - Full control over where content is stored
  - Useful for focused research on specific topics
  - Simplifies organization when you know the target KB

## Web Interface
1. In Advanced Settings, find "Knowledge Base Selection"
2. Choose between:
   - 🤖 Automatic (Smart categorization)
   - 📋 Select specific knowledge base
3. If Manual mode is selected:
   - A dropdown appears with existing knowledge bases
   - Use the refresh button to update the list
   - Select your target knowledge base

## API Usage

### Python Script
```python
from crawl_workflow import CrawlWorkflow

# Automatic mode
workflow = CrawlWorkflow(
    dify_base_url="http://localhost:8088",
    dify_api_key="your-api-key",
    knowledge_base_mode='automatic'
)

# Manual mode
workflow = CrawlWorkflow(
    dify_base_url="http://localhost:8088", 
    dify_api_key="your-api-key",
    knowledge_base_mode='manual',
    selected_knowledge_base='kb-id-here'
)
```

### REST API
```json
POST /start_crawl
{
    "url": "https://example.com",
    "knowledge_base_mode": "manual",
    "selected_knowledge_base": "kb-id-here",
    // ... other parameters
}
```

## Technical Details

### Files Modified
- `templates/index.html`: Added UI elements for KB selection
- `app.py`: Added `/knowledge_bases` endpoint and parameter handling
- `crawl_workflow.py`: Added logic for manual KB selection in `process_crawled_content()`

### Key Features
- Maintains all existing functionality (tags, duplicate detection, etc.)
- Seamless switching between modes
- Real-time knowledge base list fetching
- Clear visual feedback about selected mode