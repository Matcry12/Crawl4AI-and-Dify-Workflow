# Custom Content Analysis Model Guide

## Overview

You can now use your own custom LLM for intelligent content analysis and mode selection. This allows you to:
- Use private/local models for content filtering
- Leverage specialized models for better analysis
- Keep sensitive content analysis on your infrastructure

## How It Works

### Model Responsibilities

| Model | Purpose | Can Use Custom? |
|-------|---------|-----------------|
| **Extraction Model** | Main content processing | ✅ Custom LLM |
| **Analysis Model** | Content filtering & mode selection | ✅ Custom LLM (NEW!) |
| **Naming Model** | Knowledge base categorization | ❌ Dropdown only |

## Configuration Steps

### 1. Enable Custom LLM Provider
First, configure your custom LLM endpoint:
- Check "Use Custom LLM Provider"
- Enter your endpoint URL
- Enter your API key

### 2. Select AI-Powered Analysis
In RAG Optimization Mode:
- Choose "AI-Powered Analysis"
- In Content Analysis Model dropdown, select "➕ Use Custom LLM for Analysis..."

### 3. Complete Setup
The system will now use your custom LLM for:
- Content value assessment (skip low-value pages)
- Structure analysis (single vs multi-topic)
- Mode recommendation (full_doc vs paragraph)

## UI Flow

```
Advanced Settings
  ☑ Use Custom LLM Provider
    Custom LLM Base URL: https://your-llm.com/v1
    Custom LLM API Key: your-key

RAG Optimization Mode
  Mode Selection: 🤖 AI-Powered Analysis
    Content Analysis Model: [➕ Use Custom LLM for Analysis... ▼]
    
    📝 Note: When using custom LLM for analysis, it will use the 
    same endpoint configured in "Use Custom LLM Provider" above.
```

## Requirements

Your custom LLM must support:
1. **OpenAI-compatible API** format
2. **JSON Schema** responses
3. The following analysis schema:

```json
{
  "content_value": "high|medium|low|skip",
  "value_reason": "Brief explanation",
  "content_structure": "single_topic|multi_topic|reference|list|mixed",
  "structure_reason": "Brief explanation",
  "main_topics": ["topic1", "topic2"],
  "recommended_mode": "full_doc|paragraph",
  "mode_reason": "Why this mode is recommended",
  "content_type": "tutorial|documentation|profile|etc",
  "has_code": true|false,
  "is_navigational": true|false
}
```

## Example Configurations

### Local LLM (LM Studio)
```
Base URL: http://localhost:1234/v1
API Key: not-needed
Model: local-llama-model
```

### Together AI
```
Base URL: https://api.together.xyz/v1
API Key: your-together-key
Model: mixtral-8x7b
```

### Custom Hosted
```
Base URL: https://your-company.com/llm/v1
API Key: your-internal-key
Model: company-analysis-model
```

## Progress Log Output

When using custom analysis model:
```
🔀 Dual-Mode RAG: ENABLED
  🤖 Using AI-powered content analysis
  📊 Analysis using custom LLM: https://your-llm.com/v1
```

## Benefits

1. **Privacy**: Keep content analysis on your infrastructure
2. **Specialization**: Use models fine-tuned for your content
3. **Cost Control**: Use cheaper or free local models
4. **Consistency**: Same model for all operations

## Troubleshooting

### "Please enable Custom LLM Provider first"
- You must configure the custom LLM endpoint before selecting custom analysis
- The same endpoint is used for both extraction and analysis

### Analysis Fails
- Verify your model supports the required JSON schema
- Check API compatibility with OpenAI format
- Ensure model can handle ~5000 character inputs

### Fallback Behavior
If custom analysis fails, the system will:
1. Log the error
2. Fall back to threshold-based mode selection
3. Continue processing

## Advanced Usage

### Different Models for Different Tasks
```python
# Programmatic usage
workflow = CrawlWorkflow(
    # Use GPT-4 for extraction
    extraction_model="openai/gpt-4",
    
    # Use custom model for analysis
    use_intelligent_mode=True,
    custom_llm_base_url="https://your-llm.com/v1",
    custom_llm_api_key="your-key",
    intelligent_analysis_model="your-analysis-model"
)
```

### Testing Your Model
1. Start with a simple page
2. Check progress logs for analysis results
3. Verify filtering decisions match expectations
4. Compare with standard models

## Summary

Custom Content Analysis Model support gives you full control over:
- Which content gets processed (filtering)
- How content is categorized (mode selection)
- Where analysis happens (privacy/compliance)

This completes the intelligent RAG system with maximum flexibility!