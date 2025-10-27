# 🌐 Document Viewer Web UI - Quick Start Guide

## Launch the Web UI

Simply run:

```bash
python3 document_viewer_ui.py
```

Then open your browser to: **http://localhost:5001**

## 🎨 Features

### Beautiful Dashboard
- **Real-time Statistics**: See document count, chunks, merges, and averages
- **Gradient Design**: Modern purple gradient theme
- **Responsive**: Works on desktop, tablet, and mobile

### Document List View
- **Card Layout**: Each document shown as an attractive card
- **Hover Effects**: Cards lift up when you hover over them
- **Quick Info**: Category, keyword count visible at a glance
- **Keyword Tags**: First 5 keywords shown as colored badges
- **Summary Preview**: First 200 characters of each document

### Search Functionality
- **Real-time Search**: Type in the search box and press Enter
- **Smart Matching**: Searches titles, keywords, and summaries
- **Instant Results**: Filtered documents appear immediately

### Document Detail View
- **Full Content Display**: Complete document text in readable format
- **All Chunks Visible**: Every chunk shown with token counts
- **Metadata**: ID, category, creation date, keywords
- **Source URLs**: If available, displayed with links
- **Back Navigation**: Easy return to document list

### API Endpoints
The UI also provides JSON APIs:
- `GET /api/stats` - Database statistics
- `GET /api/documents` - All documents list
- `GET /api/document/<id>` - Single document with chunks

## 🖥️ Screenshots (Text Preview)

### Home Page:
```
┌─────────────────────────────────────────────┐
│     📚 Document Viewer                      │
│     RAG Database Explorer                   │
├─────────────────────────────────────────────┤
│  [8]           [10]         [6]        [1.2]│
│  Documents     Chunks      Merges    Avg/Doc│
├─────────────────────────────────────────────┤
│  🔍 Search documents...        [🔄 Refresh] │
├─────────────────────────────────────────────┤
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │ EOS Network Web Application...        │ │
│  │ 📁 guide  🏷️ 6 keywords              │ │
│  │ [eos] [web app] [javascript] [sdk]... │ │
│  │ Learn how to integrate...             │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │ EOS Network Smart Contracts...        │ │
│  │ 📁 concept  🏷️ 8 keywords            │ │
│  │ [smart contracts] [anatomy]...        │ │
│  │ Explore the structure of...           │ │
│  └───────────────────────────────────────┘ │
│                                             │
└─────────────────────────────────────────────┘
```

### Document Detail Page:
```
┌─────────────────────────────────────────────┐
│  [← Back to List]                           │
│                                             │
│  EOS Network Web Application Integration    │
│                                             │
│  📁 guide  🆔 eos_network...  📅 2025-10-25│
│                                             │
│  🏷️ Keywords                                │
│  [eos] [web app] [javascript] [sdk]...     │
│                                             │
│  📝 Summary                                 │
│  Learn how to integrate EOS Network...     │
│                                             │
│  📄 Full Content (931 characters)           │
│  ┌─────────────────────────────────────┐   │
│  │ After establishing a foundational   │   │
│  │ understanding of EOS smart          │   │
│  │ contracts, the next step is...      │   │
│  │ [full content here]                 │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  🧩 Chunks (1 total)                        │
│  ┌─────────────────────────────────────┐   │
│  │ Chunk 1                    187 tokens│  │
│  │ After establishing a foundational   │   │
│  │ understanding of EOS smart          │   │
│  │ contracts...                        │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

## 🎯 Usage Examples

### 1. Browse All Documents
1. Open http://localhost:5001
2. See all documents with statistics
3. Click any document card to view details

### 2. Search Documents
1. Type "smart contract" in the search box
2. Press Enter
3. See filtered results
4. Click to view any result

### 3. View Document Details
1. Click a document card
2. Scroll to read full content
3. See all chunks below
4. Click "Back to List" to return

### 4. Refresh After Workflow
1. Run workflow in another terminal: `python3 workflow_manager.py`
2. Click 🔄 Refresh button in the UI
3. See newly added documents

### 5. Use API Endpoints
```bash
# Get statistics
curl http://localhost:5001/api/stats

# Get all documents
curl http://localhost:5001/api/documents

# Get specific document
curl http://localhost:5001/api/document/<doc_id>
```

## 🚀 Integration with Other Tools

### Run Multiple Services Together

**Terminal 1: Document Viewer UI**
```bash
python3 document_viewer_ui.py
# Access at http://localhost:5001
```

**Terminal 2: Dify API**
```bash
python3 dify_api.py
# Access at http://localhost:5005
```

**Terminal 3: Run Workflow**
```bash
python3 workflow_manager.py
# Adds documents to database
```

Then refresh the Document Viewer UI to see new documents!

## 📱 Mobile Friendly

The UI automatically adapts to:
- **Desktop**: Full grid layout with multiple columns
- **Tablet**: 2-column grid
- **Mobile**: Single column, touch-friendly

## 🎨 Design Features

- **Purple Gradient Theme**: Modern, professional look
- **Smooth Animations**: Cards lift on hover, smooth transitions
- **Readable Typography**: System fonts, proper line height
- **Color-Coded Tags**: Keywords shown as gradient badges
- **Shadow Effects**: Depth with subtle shadows
- **Responsive Grid**: Adapts to screen size

## 🔧 Technical Details

- **Framework**: Flask (lightweight Python web framework)
- **Port**: 5001 (different from Dify API on 5005)
- **Database**: Direct connection to PostgreSQL
- **Styling**: Pure CSS, no external dependencies
- **APIs**: RESTful JSON endpoints available

## 💡 Tips

1. **Keep it Running**: Leave the UI running while you work
2. **Use Refresh**: Click refresh after adding new documents
3. **Search is Fast**: No need to wait, instant results
4. **Mobile Access**: Access from phone/tablet on same network
5. **API Available**: Use endpoints for automation

## 🛑 Stop the Server

Press **Ctrl+C** in the terminal where the UI is running

## 🎉 Enjoy!

The Web UI makes it super easy to explore your RAG database. No command line needed once it's running - just point, click, and browse!

---

**Server URL**: http://localhost:5001
**Alternative**: http://192.168.100.18:5001 (network access)
