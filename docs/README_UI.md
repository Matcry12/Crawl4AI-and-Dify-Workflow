# Crawl4AI Web UI

A simple web interface for the Crawl4AI intelligent web crawler with Dify integration.

## Features

- 🌐 Easy-to-use web interface
- 📊 Real-time progress updates
- 🔍 Duplicate document detection (saves LLM tokens)
- 🏷️ Automatic categorization and tagging
- 📚 Direct integration with Dify knowledge base
- 🔄 Retry mechanism for failed extractions

## Installation

1. Install UI dependencies:
```bash
pip install -r requirements_ui.txt
```

2. Make sure you have the main Crawl4AI dependencies installed

## Configuration

1. Set your Gemini API key in `.env` file:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

2. Update Dify settings in the UI:
   - Base URL: Default is `http://localhost:8088`
   - API Key: Your Dify dataset API key

## Running the UI

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

## Usage

1. **Enter URL**: Input the website you want to crawl
2. **Set Parameters**:
   - **Max Pages**: Maximum number of pages to crawl (default: 10)
   - **Max Depth**: How deep to crawl from the starting URL (default: 0)
3. **Advanced Settings** (optional):
   - Configure Dify base URL and API key
4. **Start Crawling**: Click the button and watch real-time progress

## How It Works

1. **Phase 1**: Discovers all URLs and checks for existing documents
2. **Phase 2**: Extracts content only for new URLs (saves tokens!)
3. **Processing**: Categorizes content and pushes to appropriate knowledge bases
4. **Summary**: Shows statistics including duplicates skipped

## Features

- **Token Saving**: Skips extraction for documents that already exist
- **Auto-Retry**: Automatically retries failed extractions (up to 2 times)
- **Real-time Updates**: See progress as it happens
- **Smart Categorization**: Automatically organizes content into knowledge bases
- **Consistent Naming**: URLs are consistently named to prevent duplicates

## API Endpoints

- `GET /` - Main UI
- `POST /start_crawl` - Start a new crawl
- `GET /progress` - Server-sent events for progress updates
- `GET /status` - Check if a crawl is running