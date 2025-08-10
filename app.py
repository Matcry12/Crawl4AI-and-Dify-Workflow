import asyncio
import os
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import json
import threading
import queue
from datetime import datetime
from crawl_workflow import CrawlWorkflow
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)
CORS(app)

# Global queue for progress updates
progress_queue = queue.Queue()
current_task = None
task_lock = threading.Lock()
cancel_event = threading.Event()
current_loop = None

def run_async_crawl(url, max_pages, max_depth, api_key, base_url, llm_api_key, extraction_model, naming_model=None, knowledge_base_mode='automatic', selected_knowledge_base=None):
    """Run the async crawl in a separate thread with dual-model support."""
    global current_task, current_loop
    
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    current_loop = loop
    
    # Clear cancel event
    cancel_event.clear()
    
    try:
        # Determine which API key to use based on models
        api_key_to_use = llm_api_key
        if not api_key_to_use:
            # Try to get from environment based on provider
            # Check extraction model first, then naming model
            model_to_check = extraction_model or naming_model
            if model_to_check and model_to_check.startswith('gemini/'):
                api_key_to_use = os.getenv('GEMINI_API_KEY')
            elif model_to_check and model_to_check.startswith('openai/'):
                api_key_to_use = os.getenv('OPENAI_API_KEY')
            elif model_to_check and model_to_check.startswith('anthropic/'):
                api_key_to_use = os.getenv('ANTHROPIC_API_KEY')
        
        # Use default naming model if not specified
        if not naming_model:
            naming_model = "gemini/gemini-1.5-flash"  # Default to fast model
        
        progress_queue.put({
            'type': 'log',
            'message': f'🧠 Dual-Model Configuration:',
            'timestamp': datetime.now().isoformat()
        })
        progress_queue.put({
            'type': 'log',
            'message': f'  📝 Naming: {naming_model} (fast categorization)',
            'timestamp': datetime.now().isoformat()
        })
        progress_queue.put({
            'type': 'log',
            'message': f'  🔍 Extraction: {extraction_model} (smart content processing)',
            'timestamp': datetime.now().isoformat()
        })
        
        # Create workflow instance with dual-model support
        workflow = CrawlWorkflow(
            dify_base_url=base_url,
            dify_api_key=api_key,
            gemini_api_key=api_key_to_use,
            naming_model=naming_model,  # Add naming model parameter
            knowledge_base_mode=knowledge_base_mode,
            selected_knowledge_base=selected_knowledge_base
        )
        
        # Monkey patch print to capture output
        original_print = print
        def custom_print(*args, **kwargs):
            message = ' '.join(str(arg) for arg in args)
            progress_queue.put({
                'type': 'log',
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
            original_print(*args, **kwargs)
        
        import builtins
        builtins.print = custom_print
        
        # Check for cancellation periodically
        async def crawl_with_cancel_check():
            # Create a task for the crawl
            crawl_task = asyncio.create_task(
                workflow.crawl_and_process(
                    url=url,
                    max_pages=max_pages,
                    max_depth=max_depth,
                    extraction_model=extraction_model
                )
            )
            
            while not crawl_task.done():
                if cancel_event.is_set():
                    crawl_task.cancel()
                    progress_queue.put({
                        'type': 'cancelled',
                        'message': 'Crawl cancelled by user',
                        'timestamp': datetime.now().isoformat()
                    })
                    break
                await asyncio.sleep(0.5)
            
            if not crawl_task.cancelled():
                await crawl_task
        
        # Run the crawl
        loop.run_until_complete(crawl_with_cancel_check())
        
        progress_queue.put({
            'type': 'complete',
            'message': 'Crawl completed successfully!',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        progress_queue.put({
            'type': 'error',
            'message': f'Error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        })
    finally:
        # Restore original print
        builtins.print = original_print
        with task_lock:
            current_task = None
        loop.close()

@app.route('/')
def index():
    """Render the main UI."""
    return render_template('index.html')

@app.route('/start_crawl', methods=['POST'])
def start_crawl():
    """Start a new crawl task."""
    global current_task
    
    with task_lock:
        if current_task is not None:
            return jsonify({
                'status': 'error',
                'message': 'A crawl is already in progress'
            }), 400
    
    data = request.json
    url = data.get('url')
    max_pages = int(data.get('max_pages', 10))
    max_depth = int(data.get('max_depth', 0))
    api_key = data.get('api_key', 'dataset-VoYPMEaQ8L1udk2F6oek99XK')
    base_url = data.get('base_url', 'http://localhost:8088')
    llm_api_key = data.get('llm_api_key', '')
    extraction_model = data.get('extraction_model', 'gemini/gemini-2.0-flash-exp')
    naming_model = data.get('naming_model', 'gemini/gemini-1.5-flash')
    knowledge_base_mode = data.get('knowledge_base_mode', 'automatic')
    selected_knowledge_base = data.get('selected_knowledge_base', None)
    
    if not url:
        return jsonify({
            'status': 'error',
            'message': 'URL is required'
        }), 400
    
    # Check if API key is provided or available in environment
    if not llm_api_key:
        env_key = None
        # Check both models for API key requirement
        primary_model = extraction_model or naming_model
        if primary_model.startswith('gemini/'):
            env_key = os.getenv('GEMINI_API_KEY')
        elif primary_model.startswith('openai/'):
            env_key = os.getenv('OPENAI_API_KEY')
        elif primary_model.startswith('anthropic/'):
            env_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not env_key:
            return jsonify({
                'status': 'error',
                'message': f'API key is required for models {naming_model} and {extraction_model}. Please provide it in the form or set it in .env file.'
            }), 400
    
    # Clear previous progress
    while not progress_queue.empty():
        progress_queue.get()
    
    # Start crawl in background thread
    with task_lock:
        current_task = threading.Thread(
            target=run_async_crawl,
            args=(url, max_pages, max_depth, api_key, base_url, llm_api_key, extraction_model, naming_model, knowledge_base_mode, selected_knowledge_base)
        )
        current_task.start()
    
    return jsonify({
        'status': 'success',
        'message': 'Crawl started successfully'
    })

@app.route('/progress')
def progress():
    """Stream progress updates using Server-Sent Events."""
    def generate():
        while True:
            try:
                # Get message from queue with timeout
                message = progress_queue.get(timeout=1)
                yield f"data: {json.dumps(message)}\n\n"
                
                # Check if task is complete
                if message.get('type') in ['complete', 'error']:
                    break
                    
            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                
                # Check if task is still running
                with task_lock:
                    if current_task is None:
                        yield f"data: {json.dumps({'type': 'complete', 'message': 'No active task'})}\n\n"
                        break
    
    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/status')
def status():
    """Get current crawl status."""
    with task_lock:
        is_running = current_task is not None
    
    return jsonify({
        'is_running': is_running
    })

@app.route('/knowledge_bases')
def get_knowledge_bases():
    """Get list of available knowledge bases."""
    try:
        # Get Dify configuration from request args or use defaults
        base_url = request.args.get('base_url', 'http://localhost:8088')
        api_key = request.args.get('api_key', 'dataset-VoYPMEaQ8L1udk2F6oek99XK')
        
        # Import DifyAPI
        from Test_dify import DifyAPI
        dify_api = DifyAPI(base_url=base_url, api_key=api_key)
        
        # Get knowledge bases
        response = dify_api.get_knowledge_base_list()
        
        knowledge_bases = {}
        if response.status_code == 200:
            kb_data = response.json()
            
            # Handle different possible response structures
            kb_list = []
            if isinstance(kb_data, dict):
                if 'data' in kb_data:
                    kb_list = kb_data['data']
                elif 'datasets' in kb_data:
                    kb_list = kb_data['datasets']
            elif isinstance(kb_data, list):
                kb_list = kb_data
            
            # Process knowledge bases
            for kb in kb_list:
                if isinstance(kb, dict):
                    kb_name = kb.get('name') or kb.get('title') or kb.get('dataset_name')
                    kb_id = kb.get('id') or kb.get('dataset_id') or kb.get('uuid')
                    
                    if kb_name and kb_id:
                        knowledge_bases[kb_name] = kb_id
        
        return jsonify({
            'status': 'success',
            'knowledge_bases': knowledge_bases
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'knowledge_bases': {}
        }), 500

@app.route('/cancel', methods=['POST'])
def cancel_crawl():
    """Cancel the current crawl."""
    global current_loop
    
    with task_lock:
        if current_task is None:
            return jsonify({
                'status': 'error',
                'message': 'No crawl is currently running'
            }), 400
    
    # Set cancel event
    cancel_event.set()
    
    return jsonify({
        'status': 'success',
        'message': 'Cancel request sent'
    })

if __name__ == '__main__':
    app.run(debug=True, threaded=True, port=5000)