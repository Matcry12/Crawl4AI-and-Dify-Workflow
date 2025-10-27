#!/bin/bash

################################################################################
# RAG Pipeline Manager
# Manages PostgreSQL database, Dify API, and Web UI for Crawl4AI RAG system
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

POSTGRES_CONTAINER="postgres-crawl4ai"
POSTGRES_PORT="5432"
DIFY_API_PORT="5005"
WEB_UI_PORT="5001"

# PID files
DIFY_API_PID_FILE="/tmp/dify_api.pid"
WEB_UI_PID_FILE="/tmp/web_ui.pid"

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo ""
    echo -e "${PURPLE}================================================================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}================================================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is not installed"
        exit 1
    fi
}

################################################################################
# Database Functions
################################################################################

start_database() {
    print_header "Starting PostgreSQL Database"

    check_docker

    # Check if container exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
        # Container exists, check if running
        if docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
            print_success "Database already running"
        else
            print_info "Starting existing container..."
            docker start "$POSTGRES_CONTAINER"
            sleep 2
            print_success "Database started"
        fi
    else
        print_info "Creating new PostgreSQL container..."
        docker run -d \
            --name "$POSTGRES_CONTAINER" \
            -e POSTGRES_USER=postgres \
            -e POSTGRES_PASSWORD=postgres \
            -e POSTGRES_DB=crawl4ai \
            -p "${POSTGRES_PORT}:5432" \
            -v crawl4ai_data:/var/lib/postgresql/data \
            pgvector/pgvector:pg16

        sleep 5
        print_success "Database created and started"
    fi

    # Show database info
    echo ""
    print_info "Database Information:"
    echo "   Container: $POSTGRES_CONTAINER"
    echo "   Port: $POSTGRES_PORT"
    echo "   Database: crawl4ai"
    echo "   User: postgres"
    echo "   Connection: postgresql://postgres:postgres@localhost:5432/crawl4ai"
}

stop_database() {
    print_header "Stopping PostgreSQL Database"

    if docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
        docker stop "$POSTGRES_CONTAINER"
        print_success "Database stopped"
    else
        print_warning "Database not running"
    fi
}

database_status() {
    if docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
        print_success "Database is running"

        # Get document count
        DOC_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U postgres -d crawl4ai -t -c "SELECT COUNT(*) FROM documents;" 2>/dev/null | tr -d ' ' || echo "0")
        CHUNK_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U postgres -d crawl4ai -t -c "SELECT COUNT(*) FROM chunks;" 2>/dev/null | tr -d ' ' || echo "0")

        echo "   Documents: $DOC_COUNT"
        echo "   Chunks: $CHUNK_COUNT"
    else
        print_error "Database is not running"
        return 1
    fi
}

################################################################################
# API Functions
################################################################################

start_dify_api() {
    print_header "Starting Dify API"

    check_python

    # Check if already running
    if [ -f "$DIFY_API_PID_FILE" ]; then
        PID=$(cat "$DIFY_API_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            print_warning "Dify API already running (PID: $PID)"
            return 0
        fi
    fi

    # Start API
    print_info "Starting Dify API on port $DIFY_API_PORT..."

    if [ ! -f "dify_api.py" ]; then
        print_error "dify_api.py not found"
        return 1
    fi

    # Check for .env file
    if [ ! -f ".env" ]; then
        print_warning ".env file not found, using defaults"
    fi

    # Start in background
    nohup python3 dify_api.py > logs/dify_api.log 2>&1 &
    PID=$!
    echo "$PID" > "$DIFY_API_PID_FILE"

    sleep 2

    # Verify it started
    if ps -p "$PID" > /dev/null 2>&1; then
        print_success "Dify API started (PID: $PID)"
        echo "   URL: http://localhost:$DIFY_API_PORT"
        echo "   Endpoint: http://localhost:$DIFY_API_PORT/retrieval"
        echo "   Logs: logs/dify_api.log"
    else
        print_error "Failed to start Dify API"
        rm -f "$DIFY_API_PID_FILE"
        return 1
    fi
}

stop_dify_api() {
    print_header "Stopping Dify API"

    if [ -f "$DIFY_API_PID_FILE" ]; then
        PID=$(cat "$DIFY_API_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            rm -f "$DIFY_API_PID_FILE"
            print_success "Dify API stopped"
        else
            print_warning "Dify API not running"
            rm -f "$DIFY_API_PID_FILE"
        fi
    else
        print_warning "No PID file found"
    fi
}

dify_api_status() {
    if [ -f "$DIFY_API_PID_FILE" ]; then
        PID=$(cat "$DIFY_API_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            print_success "Dify API is running (PID: $PID)"
            echo "   URL: http://localhost:$DIFY_API_PORT"

            # Test connection
            if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$DIFY_API_PORT/health" 2>/dev/null | grep -q "200"; then
                print_success "API responding to health checks"
            fi
        else
            print_error "Dify API is not running"
            rm -f "$DIFY_API_PID_FILE"
            return 1
        fi
    else
        print_error "Dify API is not running"
        return 1
    fi
}

################################################################################
# Web UI Functions
################################################################################

start_web_ui() {
    print_header "Starting Web UI"

    check_python

    # Check if already running
    if [ -f "$WEB_UI_PID_FILE" ]; then
        PID=$(cat "$WEB_UI_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            print_warning "Web UI already running (PID: $PID)"
            return 0
        fi
    fi

    # Start UI
    print_info "Starting Web UI on port $WEB_UI_PORT..."

    if [ ! -f "integrated_web_ui.py" ]; then
        print_error "integrated_web_ui.py not found"
        return 1
    fi

    # Load GEMINI_API_KEY
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | grep GEMINI_API_KEY | xargs)
    fi

    if [ -z "$GEMINI_API_KEY" ]; then
        print_error "GEMINI_API_KEY not found in .env"
        return 1
    fi

    # Start in background
    nohup python3 integrated_web_ui.py > logs/web_ui.log 2>&1 &
    PID=$!
    echo "$PID" > "$WEB_UI_PID_FILE"

    sleep 3

    # Verify it started
    if ps -p "$PID" > /dev/null 2>&1; then
        print_success "Web UI started (PID: $PID)"
        echo "   URL: http://localhost:$WEB_UI_PORT"
        echo "   Features:"
        echo "     • Workflow Manager (configure and run crawls)"
        echo "     • Document Viewer (browse database)"
        echo "     • Statistics Dashboard"
        echo "   Logs: logs/web_ui.log"
    else
        print_error "Failed to start Web UI"
        rm -f "$WEB_UI_PID_FILE"
        return 1
    fi
}

stop_web_ui() {
    print_header "Stopping Web UI"

    if [ -f "$WEB_UI_PID_FILE" ]; then
        PID=$(cat "$WEB_UI_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            rm -f "$WEB_UI_PID_FILE"
            print_success "Web UI stopped"
        else
            print_warning "Web UI not running"
            rm -f "$WEB_UI_PID_FILE"
        fi
    else
        print_warning "No PID file found"
    fi
}

web_ui_status() {
    if [ -f "$WEB_UI_PID_FILE" ]; then
        PID=$(cat "$WEB_UI_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            print_success "Web UI is running (PID: $PID)"
            echo "   URL: http://localhost:$WEB_UI_PORT"
        else
            print_error "Web UI is not running"
            rm -f "$WEB_UI_PID_FILE"
            return 1
        fi
    else
        print_error "Web UI is not running"
        return 1
    fi
}

################################################################################
# Combined Functions
################################################################################

start_all() {
    print_header "🚀 Starting Complete RAG Pipeline"

    # Create logs directory
    mkdir -p logs

    # Start services in order
    start_database
    echo ""
    sleep 2

    start_dify_api
    echo ""
    sleep 2

    start_web_ui
    echo ""

    print_header "✅ RAG Pipeline Started Successfully"

    echo -e "${GREEN}🎉 All services are running!${NC}"
    echo ""
    echo "📊 Access Points:"
    echo "   • Web UI:       http://localhost:$WEB_UI_PORT"
    echo "   • Dify API:     http://localhost:$DIFY_API_PORT"
    echo "   • Database:     localhost:$POSTGRES_PORT"
    echo ""
    echo "📝 Next Steps:"
    echo "   1. Open http://localhost:$WEB_UI_PORT in your browser"
    echo "   2. Go to 'Workflow' tab to run a crawl"
    echo "   3. Configure URL, pages, and LLM model"
    echo "   4. Click 'Start Workflow' and watch live logs"
    echo "   5. View results in 'Documents' tab"
    echo ""
    echo "📋 Logs:"
    echo "   • Web UI:   tail -f logs/web_ui.log"
    echo "   • Dify API: tail -f logs/dify_api.log"
    echo ""
}

stop_all() {
    print_header "🛑 Stopping RAG Pipeline"

    stop_web_ui
    echo ""

    stop_dify_api
    echo ""

    stop_database
    echo ""

    print_success "All services stopped"
}

restart_all() {
    print_header "🔄 Restarting RAG Pipeline"
    stop_all
    sleep 2
    start_all
}

status_all() {
    print_header "📊 RAG Pipeline Status"

    echo -e "${CYAN}Database:${NC}"
    database_status || true
    echo ""

    echo -e "${CYAN}Dify API:${NC}"
    dify_api_status || true
    echo ""

    echo -e "${CYAN}Web UI:${NC}"
    web_ui_status || true
    echo ""
}

show_logs() {
    SERVICE=$1

    case $SERVICE in
        "ui"|"web"|"webui")
            if [ -f "logs/web_ui.log" ]; then
                tail -f logs/web_ui.log
            else
                print_error "Log file not found: logs/web_ui.log"
            fi
            ;;
        "api"|"dify")
            if [ -f "logs/dify_api.log" ]; then
                tail -f logs/dify_api.log
            else
                print_error "Log file not found: logs/dify_api.log"
            fi
            ;;
        *)
            print_error "Unknown service: $SERVICE"
            echo "Available: ui, api"
            ;;
    esac
}

################################################################################
# Main Menu
################################################################################

show_menu() {
    clear
    print_header "🤖 RAG Pipeline Manager"

    echo "Select an option:"
    echo ""
    echo "  ${GREEN}1)${NC} Start all services"
    echo "  ${GREEN}2)${NC} Stop all services"
    echo "  ${GREEN}3)${NC} Restart all services"
    echo "  ${GREEN}4)${NC} Check status"
    echo ""
    echo "  ${BLUE}5)${NC} Start database only"
    echo "  ${BLUE}6)${NC} Start Dify API only"
    echo "  ${BLUE}7)${NC} Start Web UI only"
    echo ""
    echo "  ${YELLOW}8)${NC} View Web UI logs"
    echo "  ${YELLOW}9)${NC} View Dify API logs"
    echo ""
    echo "  ${RED}0)${NC} Exit"
    echo ""
    echo -n "Enter choice: "
}

interactive_menu() {
    while true; do
        show_menu
        read choice

        case $choice in
            1) start_all; read -p "Press Enter to continue..."; ;;
            2) stop_all; read -p "Press Enter to continue..."; ;;
            3) restart_all; read -p "Press Enter to continue..."; ;;
            4) status_all; read -p "Press Enter to continue..."; ;;
            5) start_database; read -p "Press Enter to continue..."; ;;
            6) start_dify_api; read -p "Press Enter to continue..."; ;;
            7) start_web_ui; read -p "Press Enter to continue..."; ;;
            8) show_logs "ui"; ;;
            9) show_logs "api"; ;;
            0) exit 0 ;;
            *) print_error "Invalid option"; sleep 1; ;;
        esac
    done
}

################################################################################
# Command Line Interface
################################################################################

show_help() {
    echo "RAG Pipeline Manager"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start          Start all services (database, API, UI)"
    echo "  stop           Stop all services"
    echo "  restart        Restart all services"
    echo "  status         Show status of all services"
    echo ""
    echo "  start-db       Start database only"
    echo "  start-api      Start Dify API only"
    echo "  start-ui       Start Web UI only"
    echo ""
    echo "  stop-db        Stop database only"
    echo "  stop-api       Stop Dify API only"
    echo "  stop-ui        Stop Web UI only"
    echo ""
    echo "  logs-ui        Show Web UI logs (tail -f)"
    echo "  logs-api       Show Dify API logs (tail -f)"
    echo ""
    echo "  menu           Show interactive menu"
    echo "  help           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 start       # Start everything"
    echo "  $0 status      # Check what's running"
    echo "  $0 logs-ui     # Watch UI logs"
    echo ""
}

################################################################################
# Entry Point
################################################################################

# Check if no arguments
if [ $# -eq 0 ]; then
    interactive_menu
    exit 0
fi

# Parse command
COMMAND=$1

case $COMMAND in
    "start")
        start_all
        ;;
    "stop")
        stop_all
        ;;
    "restart")
        restart_all
        ;;
    "status")
        status_all
        ;;
    "start-db")
        start_database
        ;;
    "start-api")
        start_dify_api
        ;;
    "start-ui")
        start_web_ui
        ;;
    "stop-db")
        stop_database
        ;;
    "stop-api")
        stop_dify_api
        ;;
    "stop-ui")
        stop_web_ui
        ;;
    "logs-ui")
        show_logs "ui"
        ;;
    "logs-api")
        show_logs "api"
        ;;
    "menu")
        interactive_menu
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac
