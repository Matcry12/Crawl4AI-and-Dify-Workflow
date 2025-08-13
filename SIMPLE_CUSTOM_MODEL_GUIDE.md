# Simple Custom Model Guide

## How to Use Custom Models (Easy Way!)

### For Content Extraction

1. In **Extraction Model** dropdown, select **"➕ Custom Model..."**
2. Type your model name (e.g., `llama-2-13b`, `mistral-7b`)
3. Done! ✅

### For Content Analysis (Filtering & Mode Selection)

1. Select **"AI-Powered Analysis"** mode
2. In **Content Analysis Model** dropdown, select **"➕ Custom Model..."**
3. Type your model name (e.g., `llama-2-13b`, `mistral-7b`)
4. Done! ✅

### For Both? Just Need One Custom LLM Setup!

1. Check **"☑ Use Custom LLM Provider"**
2. Enter your endpoint:
   - **Base URL**: `https://your-llm.com/v1`
   - **API Key**: `your-key`
3. Now both dropdowns can use custom models!

## Examples

### Local Model (LM Studio)
```
☑ Use Custom LLM Provider
Base URL: http://localhost:1234/v1
API Key: not-needed

Extraction Model: ➕ Custom Model... → llama-2-13b-chat
Analysis Model: ➕ Custom Model... → llama-2-7b
```

### Together AI
```
☑ Use Custom LLM Provider  
Base URL: https://api.together.xyz/v1
API Key: your-together-key

Extraction Model: ➕ Custom Model... → mixtral-8x7b-instruct
Analysis Model: ➕ Custom Model... → llama-2-7b-chat
```

### OpenRouter
```
☑ Use Custom LLM Provider
Base URL: https://openrouter.ai/api/v1
API Key: your-openrouter-key

Extraction Model: ➕ Custom Model... → anthropic/claude-instant
Analysis Model: ➕ Custom Model... → meta-llama/llama-2-13b-chat
```

## That's It! 🎉

No complex configuration needed. Just:
1. Enable custom LLM
2. Select "Custom Model..." 
3. Type the model name
4. Go!

The UI now works exactly like the other model selections - simple and consistent!