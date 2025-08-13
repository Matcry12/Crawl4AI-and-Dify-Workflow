# UI Guide: Intelligent RAG Mode

This guide shows you how to use the intelligent RAG mode features in the web UI.

## Starting the UI

```bash
python app.py
```

Then open your browser to: http://localhost:5000

## Using Intelligent RAG Mode

### 1. Open Advanced Settings

Click the "▶ Advanced Settings" button to expand all options.

### 2. Configure Custom LLM Provider (Optional)

If you want to use your own LLM:
- Check "Use Custom LLM Provider" checkbox
- Enter your custom LLM details:
  - **Base URL**: Your OpenAI-compatible API endpoint (e.g., `https://your-llm.com/v1`)
  - **API Key**: Your custom LLM API key
- Supported: Any OpenAI-compatible API, Local LLMs, Together AI, etc.

### 3. Find RAG Optimization Mode Section

Scroll down to find the "🔀 RAG Optimization Mode" section. This is where you configure the intelligent features.

### 4. Enable Dual-Mode RAG

The checkbox "Enable Dual-Mode RAG Optimization" should be checked by default. This enables automatic mode selection.

### 5. Choose Mode Selection Strategy

You have three options:

#### A. Word Count Threshold (Default)
- **What it does**: Uses simple word count to decide mode
- **When to use**: Predictable content, fast processing
- **Configuration**: Set the word threshold (default 4000 words)
  - ≤ 4000 words → Full Doc Mode
  - > 4000 words → Paragraph Mode

#### B. AI-Powered Analysis (Intelligent)
- **What it does**: Uses AI to analyze content structure
- **When to use**: Mixed content types, want smart filtering
- **Configuration**: Select analysis model (Gemini 1.5 Flash recommended)
- **Benefits**:
  - Skips low-value pages (login, navigation, ads)
  - Chooses mode based on content structure
  - Better RAG performance

#### C. Manual Selection (Force Mode)
- **What it does**: Forces all content to use a specific mode
- **When to use**: Testing, debugging, or when you know content structure
- **Options**:
  - **Full Doc Mode**: Returns entire documents when any chunk matches
  - **Paragraph Mode**: Returns only matching chunks
- **Access**: Select "Manual Selection" from dropdown, then choose mode

## What to Look For in Progress Log

### With Word Count Threshold:
```
🔀 Dual-Mode RAG: ENABLED
  📏 Using word count threshold: 4000 words
📊 Content analysis:
   📝 Word count: 3,247 words
📄 Selected mode: full_doc
   ℹ️ Content has 3247 words (≤ 4000 words threshold)
```

### With AI-Powered Analysis:
```
🔀 Dual-Mode RAG: ENABLED
  🤖 Using AI-powered content analysis
  📊 Analysis model: gemini/gemini-1.5-flash
🤖 Running intelligent content analysis...
📊 Intelligent analysis results:
   🎯 Content value: high
   📋 Structure: single_topic
   📝 Type: tutorial
   🔍 Main topics: python, web scraping, automation
📄 Selected mode: full_doc
   ℹ️ Single-topic tutorial - best retrieved as complete document
```

### Skipped Pages (Intelligent Mode Only):
```
⏭️ Skipping page: Low value navigational page
   Content value: low
```

### With Manual Mode:
```
🔀 Dual-Mode RAG: ENABLED
  ✋ Manual mode: PARAGRAPH
[1/5] Processing: https://example.com/docs
  🔍 Mode selection process:
  ✋ Manual mode: PARAGRAPH
```

### With Custom LLM:
```
🔧 Custom LLM: https://api.together.xyz/v1
🔀 Dual-Mode RAG: ENABLED
  🤖 Using AI-powered content analysis
  📊 Analysis model: gemini/gemini-1.5-flash
```

## UI Features

### Visual Indicators

1. **Mode Selection Display**: Shows current configuration
2. **Real-time Progress**: See analysis decisions as they happen
3. **Color-coded Logs**: 
   - 🟢 Success (green)
   - 🟡 Skipped/Warning (yellow)
   - 🔵 Info (blue)
   - 🔴 Error (red)

### Interactive Elements

1. **Mode Dropdown**: Switch between threshold and intelligent
2. **Threshold Slider**: Adjust word count threshold (500-20,000)
3. **Model Selection**: Choose AI model for analysis
4. **Info Boxes**: Explanations of how each mode works

## Best Practices

### For Testing:
1. Start with a small crawl (1-2 pages)
2. Try both modes on the same URL to see differences
3. Check the progress log carefully

### For Production:
1. **Simple Sites**: Use word count threshold
2. **Complex Sites**: Use AI-powered analysis
3. **Mixed Content**: Always use AI-powered analysis

## Troubleshooting

### "API key is required"
- Add your Gemini API key to the form or .env file
- The intelligent mode needs API access for content analysis

### "Intelligent analysis failed"
- Check API key is valid
- Try a different analysis model
- Falls back to threshold mode automatically

### No mode selection happening
- Make sure "Enable Dual-Mode RAG" is checked
- Check advanced settings are expanded
- Verify you're looking at the right log section

## Complete Feature Matrix

| Strategy | Description | Use Case |
|----------|-------------|----------|
| Word Count Threshold | Automatic based on length | General use |
| AI-Powered Analysis | Smart content analysis | Mixed content |
| Manual Selection | Force specific mode | Testing/Known content |

## API Support

All features work through the API as well:

```python
workflow = CrawlWorkflow(
    # ... other params
    manual_mode='full_doc',  # or 'paragraph'
    custom_llm_base_url='https://your-llm.com/v1',
    custom_llm_api_key='your-key'
)
```

## Quick Test

1. Use this test URL: `https://docs.python.org/3/tutorial/introduction.html`
2. Set max pages to 1
3. Try all three modes: threshold, intelligent, and manual
4. Compare the results in the progress log

The UI now fully supports all intelligent RAG features for optimal content processing!