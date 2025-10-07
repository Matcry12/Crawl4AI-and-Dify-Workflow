import asyncio
import os
import logging
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import json
import threading
import queue
from datetime import datetime
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.crawl_workflow import CrawlWorkflow
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

# Custom logging handler to capture logs and send to UI
class QueueHandler(logging.Handler):
    """Custom logging handler that sends logs to the progress queue for UI display."""

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        """Send log record to the queue."""
        try:
            # Format the log message
            msg = self.format(record)

            # Determine message type based on log level
            if record.levelno >= logging.ERROR:
                msg_type = 'error'
            elif record.levelno >= logging.WARNING:
                msg_type = 'warning'
            else:
                msg_type = 'log'

            # Put in queue for UI
            self.log_queue.put({
                'type': msg_type,
                'message': msg,
                'level': record.levelname,
                'timestamp': datetime.now().isoformat()
            })
        except Exception:
            self.handleError(record)

def run_async_crawl(url, max_pages, max_depth, api_key, base_url, llm_api_key, extraction_model, naming_model=None, knowledge_base_mode='automatic', selected_knowledge_base=None, enable_dual_mode=True, dual_mode_type='threshold', word_threshold=4000, use_intelligent_mode=False, intelligent_analysis_model='gemini/gemini-1.5-flash', manual_mode=None, custom_llm_base_url=None, custom_llm_api_key=None, enable_connection_pooling=True, enable_retry=True, enable_circuit_breaker=True):
    """Run the async crawl in a separate thread with dual-model, dual-mode, and performance settings support."""
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
            naming_model = "gemini/gemini-2.5-flash-lite"  # Default to Gemini 2.5 Flash Lite
        
        progress_queue.put({
            'type': 'log',
            'message': f'🧠 Model Configuration:',
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
        
        # Log dual-mode configuration
        if enable_dual_mode:
            progress_queue.put({
                'type': 'log',
                'message': f'🔀 Dual-Mode RAG: ENABLED',
                'timestamp': datetime.now().isoformat()
            })
            if manual_mode:
                progress_queue.put({
                    'type': 'log',
                    'message': f'  ✋ Manual mode: {manual_mode.upper()}',
                    'timestamp': datetime.now().isoformat()
                })
            elif use_intelligent_mode:
                progress_queue.put({
                    'type': 'log',
                    'message': f'  🤖 Using AI-powered content analysis',
                    'timestamp': datetime.now().isoformat()
                })
                # Check if using custom analysis model
                is_custom_analysis = not any(intelligent_analysis_model.startswith(p) for p in ['gemini/', 'openai/', 'anthropic/'])
                
                if custom_llm_base_url and is_custom_analysis:
                    progress_queue.put({
                        'type': 'log',
                        'message': f'  📊 Analysis model: {intelligent_analysis_model} (via custom LLM)',
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    progress_queue.put({
                        'type': 'log',
                        'message': f'  📊 Analysis model: {intelligent_analysis_model}',
                        'timestamp': datetime.now().isoformat()
                    })
            else:
                progress_queue.put({
                    'type': 'log',
                    'message': f'  📏 Using word count threshold: {word_threshold} words',
                    'timestamp': datetime.now().isoformat()
                })
        else:
            progress_queue.put({
                'type': 'log',
                'message': f'📄 Single mode: Using parent-child chunking',
                'timestamp': datetime.now().isoformat()
            })
        
        # Log custom LLM if provided
        if custom_llm_base_url:
            progress_queue.put({
                'type': 'log',
                'message': f'🔧 Custom LLM: {custom_llm_base_url}',
                'timestamp': datetime.now().isoformat()
            })
        
        # Create workflow instance with dual-model and dual-mode support
        workflow = CrawlWorkflow(
            dify_base_url=base_url,
            dify_api_key=api_key,
            gemini_api_key=api_key_to_use,
            naming_model=naming_model,
            knowledge_base_mode=knowledge_base_mode,
            selected_knowledge_base=selected_knowledge_base,
            enable_dual_mode=enable_dual_mode,
            word_threshold=word_threshold,
            use_word_threshold=True,  # Always use word threshold in UI for simplicity
            use_intelligent_mode=use_intelligent_mode,
            intelligent_analysis_model=intelligent_analysis_model,
            manual_mode=manual_mode,
            custom_llm_base_url=custom_llm_base_url,
            custom_llm_api_key=custom_llm_api_key,
            # Performance settings
            enable_connection_pooling=enable_connection_pooling,
            enable_retry=enable_retry,
            enable_circuit_breaker=enable_circuit_breaker
        )

        # Setup logging to capture logs and send to UI queue
        workflow_logger = logging.getLogger('crawl_workflow')

        # Create and configure queue handler
        queue_handler = QueueHandler(progress_queue)
        # Use simple format - just the message with emojis
        queue_handler.setFormatter(logging.Formatter('%(message)s'))

        # Remove any existing handlers and add our queue handler
        workflow_logger.handlers.clear()
        workflow_logger.addHandler(queue_handler)
        workflow_logger.setLevel(logging.INFO)  # Set to INFO to show most logs

        # Prevent propagation to root logger to avoid duplicates
        workflow_logger.propagate = False
        
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
        
        if not cancel_event.is_set():
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
        # Clean up logging handlers and restore propagation
        workflow_logger = logging.getLogger('crawl_workflow')
        workflow_logger.handlers.clear()
        workflow_logger.propagate = True  # Restore default propagation

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
    extraction_model = data.get('extraction_model', 'gemini/gemini-2.5-flash-lite')
    naming_model = data.get('naming_model', 'gemini/gemini-2.5-flash-lite')
    knowledge_base_mode = data.get('knowledge_base_mode', 'automatic')
    selected_knowledge_base = data.get('selected_knowledge_base', None)
    
    # Dual-mode RAG parameters
    enable_dual_mode = data.get('enable_dual_mode', True)
    dual_mode_type = data.get('dual_mode_type', 'threshold')
    word_threshold = int(data.get('word_threshold', 4000))
    use_intelligent_mode = data.get('use_intelligent_mode', False)
    intelligent_analysis_model = data.get('intelligent_analysis_model', 'gemini/gemini-2.5-flash-lite')
    manual_mode = data.get('manual_mode', None)  # 'full_doc' or 'paragraph'
    
    # Custom LLM parameters
    custom_llm_base_url = data.get('custom_llm_base_url', None)
    custom_llm_api_key = data.get('custom_llm_api_key', None)

    # Performance settings
    enable_connection_pooling = data.get('enable_connection_pooling', True)
    enable_retry = data.get('enable_retry', True)
    enable_circuit_breaker = data.get('enable_circuit_breaker', True)

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
            args=(url, max_pages, max_depth, api_key, base_url, llm_api_key, extraction_model, naming_model, knowledge_base_mode, selected_knowledge_base, enable_dual_mode, dual_mode_type, word_threshold, use_intelligent_mode, intelligent_analysis_model, manual_mode, custom_llm_base_url, custom_llm_api_key, enable_connection_pooling, enable_retry, enable_circuit_breaker)
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
        from tests.Test_dify import DifyAPI
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

@app.route('/stress_test', methods=['POST'])
def stress_test():
    """Run comprehensive stress test on the crawl workflow system."""
    import subprocess
    import sys

    try:
        # Run the test script
        test_path = os.path.join(os.path.dirname(__file__), '..', 'tests', 'test_crawl_workflow.py')
        result = subprocess.run(
            [sys.executable, test_path],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=os.path.join(os.path.dirname(__file__), '..')
        )

        # Read test results if available
        test_results = None
        try:
            results_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'test_results.json')
            with open(results_path, 'r') as f:
                import json
                test_results = json.load(f)
        except:
            pass

        return jsonify({
            'status': 'success' if result.returncode == 0 else 'failed',
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'test_results': test_results
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            'status': 'error',
            'message': 'Stress test timed out after 5 minutes'
        }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/quick_test', methods=['POST'])
def quick_test():
    """Run quick smoke test on the crawl workflow system."""
    import subprocess
    import sys

    try:
        # Run the quick test script
        test_path = os.path.join(os.path.dirname(__file__), '..', 'tests', 'quick_test.py')
        result = subprocess.run(
            [sys.executable, test_path],
            capture_output=True,
            text=True,
            timeout=60,  # 1 minute timeout
            cwd=os.path.join(os.path.dirname(__file__), '..')
        )

        return jsonify({
            'status': 'success' if result.returncode == 0 else 'failed',
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            'status': 'error',
            'message': 'Quick test timed out after 1 minute'
        }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, threaded=True, port=5000)