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

def run_async_crawl(url, max_pages, max_depth, api_key, base_url, llm_api_key, model):
    """Run the async crawl in a separate thread."""
    global current_task, current_loop
    
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    current_loop = loop
    
    # Clear cancel event
    cancel_event.clear()
    
    try:
        # Determine which API key to use based on model
        api_key_to_use = llm_api_key
        if not api_key_to_use:
            # Try to get from environment based on provider
            if model.startswith('gemini/'):
                api_key_to_use = os.getenv('GEMINI_API_KEY')
            elif model.startswith('openai/'):
                api_key_to_use = os.getenv('OPENAI_API_KEY')
            elif model.startswith('anthropic/'):
                api_key_to_use = os.getenv('ANTHROPIC_API_KEY')
        
        # Create workflow instance
        workflow = CrawlWorkflow(
            dify_base_url=base_url,
            dify_api_key=api_key,
            gemini_api_key=api_key_to_use  # Still using gemini_api_key param for compatibility
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
                    model=model
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
    model = data.get('model', 'gemini/gemini-2.0-flash-exp')
    
    if not url:
        return jsonify({
            'status': 'error',
            'message': 'URL is required'
        }), 400
    
    # Check if API key is provided or available in environment
    if not llm_api_key:
        env_key = None
        if model.startswith('gemini/'):
            env_key = os.getenv('GEMINI_API_KEY')
        elif model.startswith('openai/'):
            env_key = os.getenv('OPENAI_API_KEY')
        elif model.startswith('anthropic/'):
            env_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not env_key:
            return jsonify({
                'status': 'error',
                'message': f'API key is required for {model}. Please provide it in the form or set it in .env file.'
            }), 400
    
    # Clear previous progress
    while not progress_queue.empty():
        progress_queue.get()
    
    # Start crawl in background thread
    with task_lock:
        current_task = threading.Thread(
            target=run_async_crawl,
            args=(url, max_pages, max_depth, api_key, base_url, llm_api_key, model)
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