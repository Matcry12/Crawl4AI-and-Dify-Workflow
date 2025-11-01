# Integrated Web UI Guide

🎉 **New Integrated RAG Pipeline Manager is now running!**

## 🌐 Access the UI

**URL**: http://localhost:5001

The UI is now live and accessible in your web browser.

---

## ✨ Features

### 1. ⚙️ Workflow Manager (Main Page)

The workflow manager allows you to configure and run the complete RAG pipeline from a web interface.

#### Available Configuration Options:

**Basic Settings:**
- **🌐 Start URL**: The initial URL to begin crawling
  - Example: `https://docs.eosnetwork.com/docs/latest/quick-start/`
  - Can be any public website

- **📄 Max Pages**: Number of pages to crawl (1-100)
  - Start small (3-5 pages) for testing
  - Increase for production crawls

- **🤖 LLM Model**: Choose the Gemini model for topic extraction and merging
  - `gemini-2.0-flash-exp` - Experimental, fastest
  - `gemini-2.5-flash-lite` - **Default**, balanced speed/quality
  - `gemini-1.5-flash` - Stable, good quality
  - `gemini-1.5-pro` - Highest quality, slower

- **📁 Output Directory**: Where to save crawl data
  - Default: `crawl_output`

**Pipeline Stages (Checkboxes):**

- ✅ **🔒 Same Domain Only**: Only crawl pages from the same domain as start URL
  - Recommended: Keep checked to avoid crawling the entire internet

- ✅ **🏷️ Extract Topics**: Use LLM to extract topics from crawled pages
  - Required for document creation/merging

- ✅ **🤔 Merge Decision Analysis**: Analyze which topics should merge vs create new
  - Uses embedding similarity (0.85 threshold for merge, 0.4 for create)

- ✅ **📝 Create New Documents**: Create new documents for topics below similarity threshold
  - Creates fresh documents when content is sufficiently unique

- ✅ **🔀 Merge with Existing Documents**: Merge topics into existing similar documents
  - Enriches existing documents with new information
  - **Recommended**: Keep all checkboxes enabled for full pipeline

#### Workflow Execution:

1. **Configure** your settings
2. Click **🚀 Start Workflow**
3. **Watch progress** in real-time with terminal-style log
4. **Stop anytime** with ⏹ Stop button
5. **View results** when complete

#### Real-Time Progress:

When workflow is running, you'll see:
- ✅ Current stage (Crawling, Extracting, Merging)
- ⏱️ Timestamps for each operation
- 📊 Pages processed
- 🔄 Documents created/merged
- ❌ Any errors that occur

---

### 2. 📄 Documents Page

Browse all documents stored in the PostgreSQL database.

**Features:**
- **Document List**: View all documents with title, summary, and metadata
- **Statistics Cards**:
  - Total Documents
  - Total Chunks
- **Quick Info**: Document ID, chunk count, keyword count

**Use Cases:**
- Verify documents were created correctly
- Check document quality after workflow
- Browse knowledge base content

---

### 3. 📊 Statistics Page

View database metrics and health.

**Metrics Shown:**
- **Total Documents**: Number of documents in database
- **Total Chunks**: Number of text chunks (for RAG retrieval)
- **Avg Chunks/Doc**: Average chunk distribution

**Database Info:**
- Container: postgres-crawl4ai
- Database: crawl4ai
- Schema: Simplified (documents + chunks + merge_history)
- Connection Status: ✅ Connected

---

## 🎯 Quick Start Guide

### First Workflow Run:

1. **Open browser** to http://localhost:5001
2. **Keep default settings** (EOS docs, 3 pages, all checkboxes enabled)
3. **Click "🚀 Start Workflow"**
4. **Watch progress** - should take ~2 minutes for 3 pages
5. **See results** - typically 2-7 topics merged into existing documents
6. **Go to "📄 Documents"** tab to see updated documents

### Customizing for Your Needs:

**For Testing:**
- Use 1-3 pages
- Use `gemini-2.5-flash-lite` or `gemini-2.0-flash-exp`
- Keep same domain only enabled

**For Production Crawls:**
- Increase to 10-50+ pages
- Use `gemini-1.5-pro` for best quality
- Review merge/create thresholds in code if needed

**For Different Content:**
- Change start URL to your target documentation
- Adjust max pages based on site size
- Consider domain restrictions

---

## 🔧 Technical Details

### How Workflow Execution Works:

1. **Background Thread**: Workflow runs in separate thread to avoid blocking UI
2. **Progress Updates**: Real-time progress logged to workflow state
3. **Auto-Refresh**: Page checks status every 5 seconds when workflow is running
4. **Thread-Safe**: Flask runs with `threaded=True` for concurrent requests

### Workflow Stages:

```
1. 🔵 CRAWL
   └─> BFS crawler fetches pages from start URL

2. 🏷️ EXTRACT TOPICS
   └─> LLM extracts structured topics from each page

3. 🤔 MERGE DECISION
   └─> Embedding similarity determines merge vs create
   └─> LLM verifies uncertain cases (0.4-0.85 similarity)

4a. 📝 CREATE DOCUMENTS
    └─> Create new docs for unique topics (similarity < 0.4)

4b. 🔀 MERGE DOCUMENTS
    └─> Merge similar topics into existing docs (similarity ≥ 0.85)
    └─> LLM generates merged content (enrich/expand strategies)
    └─> Re-chunk merged documents
    └─> Generate new embeddings

5. 💾 SAVE TO DATABASE
   └─> Atomic transaction per page
   └─> Merge history tracked
```

### Database Schema:

```sql
-- Documents table
documents (
  id TEXT PRIMARY KEY,
  title TEXT,
  summary TEXT,
  content TEXT,
  embedding VECTOR(768),
  keywords TEXT[],
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

-- Chunks table (for RAG retrieval)
chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT REFERENCES documents(id),
  content TEXT,
  embedding VECTOR(768),
  chunk_index INTEGER,
  token_count INTEGER
)

-- Merge history (audit trail)
merge_history (
  id SERIAL PRIMARY KEY,
  target_doc_id TEXT REFERENCES documents(id),
  source_topic_title TEXT,
  merge_strategy TEXT,
  changes_made TEXT,
  merged_at TIMESTAMP
)
```

---

## 🚨 Troubleshooting

### Workflow Won't Start:
- Check that GEMINI_API_KEY is set
- Verify PostgreSQL container is running: `docker ps | grep postgres-crawl4ai`
- Check server logs in terminal

### Workflow Fails Mid-Execution:
- Check error message in UI
- Review progress log for last successful step
- Click "🔄 Clear and Retry" to reset and try again

### No Progress Updates:
- Refresh page manually
- Check browser console for JavaScript errors
- Verify workflow is actually running (check terminal)

### Documents Not Appearing:
- Check "📄 Documents" tab instead of workflow page
- Verify workflow completed successfully
- Query database directly: `docker exec postgres-crawl4ai psql -U postgres -d crawl4ai -c "SELECT COUNT(*) FROM documents;"`

### Port 5001 Already in Use:
- Check for other processes: `lsof -i :5001`
- Kill old process: `kill -9 <PID>`
- Restart integrated UI

---

## 🎨 UI Features

### Design:
- **Modern gradient theme** (Purple to blue)
- **Responsive layout** (works on mobile/tablet/desktop)
- **Card-based design** for easy scanning
- **Terminal-style logs** for progress tracking

### Navigation:
- **Tab-based navigation** at top
- **Active tab highlighted** in white
- **Smooth transitions** between pages

### Forms:
- **Clear labels** for all inputs
- **Sensible defaults** (ready to run immediately)
- **Checkbox toggles** for pipeline stages
- **Validation** (required fields, min/max values)

---

## 📝 Example Workflows

### 1. Quick Test (2-3 minutes):
```
Start URL: https://docs.eosnetwork.com/docs/latest/quick-start/
Max Pages: 3
LLM Model: gemini-2.5-flash-lite
All checkboxes: ✅
```
**Expected Result**: 2-7 topics merged into existing documents

### 2. Medium Crawl (10-15 minutes):
```
Start URL: https://docs.eosnetwork.com/docs/latest/
Max Pages: 10
LLM Model: gemini-1.5-flash
All checkboxes: ✅
```
**Expected Result**: 10-20 topics, mix of merges and new documents

### 3. Large Crawl (30+ minutes):
```
Start URL: https://your-docs-site.com/
Max Pages: 50
LLM Model: gemini-1.5-pro
All checkboxes: ✅
```
**Expected Result**: Rich knowledge base with 50+ documents

---

## 🔗 Integration with Other Tools

### Dify API (Port 5005):
The Dify API is still running on port 5005 and can query documents created by this workflow.

**Test retrieval**:
```bash
curl -X POST http://localhost:5005/retrieval \
  -H "Content-Type: application/json" \
  -d '{"query": "EOS staking", "top_k": 3}'
```

### Document Viewer (Old UI):
The old document viewer has been replaced by the integrated UI. All features are now accessible at http://localhost:5001.

---

## 🎯 Best Practices

1. **Start Small**: Test with 3-5 pages first
2. **Monitor Progress**: Watch the progress log during execution
3. **Check Results**: Visit Documents page after completion
4. **Iterate**: Adjust settings based on results
5. **Same Domain**: Keep enabled unless you specifically want cross-domain crawling

---

## 🚀 Production Deployment

For production use:

1. **Use a WSGI server** instead of Flask development server:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5001 integrated_web_ui:app
   ```

2. **Add authentication** if exposing publicly

3. **Set up reverse proxy** (nginx/Apache)

4. **Monitor resource usage** (CPU, memory, disk)

5. **Configure rate limits** for API protection

---

## 📞 Support

If you encounter issues:

1. Check this guide first
2. Review terminal logs
3. Check database connection
4. Verify API key is set
5. Test with minimal config (3 pages, default settings)

---

**Enjoy your new integrated RAG pipeline manager!** 🎉

Access it now at: **http://localhost:5001**
