#!/bin/bash

set -e

FRONTEND_DIR="desktop-electron-frontend"
BACKEND_DIR="symmetry-unified-backend"
BACKEND_PORT=8000
FRONTEND_PORT=5173

print_usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    backend         Start backend server only
    frontend        Start frontend server only
    all             Start both backend and frontend (default)
    
    reset backend   Reset and restart backend
    reset frontend  Reset and restart frontend
    reset all       Reset and restart both
    
    stop            Stop all running services
    status          Show status of services
    
    docker          Start services with Docker Compose
    docker-up       Start services with Docker Compose (detached)
    docker-down     Stop Docker Compose services
    
    help            Show this help message

Options:
    --port          Override backend port (default: 8000)
    --host          Override backend host (default: 127.0.0.1)
    --dev           Start frontend in development mode

Examples:
    $0 backend                  Start only backend
    $0 frontend --dev           Start frontend in dev mode
    $0 all --port 9000          Start both on port 9000
    $0 reset backend            Reset and restart backend
    $0 docker-up                Start with Docker Compose (detached)
EOF
}

check_backend_requirements() {
    echo "Checking backend requirements..."
    cd "$BACKEND_DIR"
    
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment with Python 3.13..."
        if ! command -v python3.13 &> /dev/null; then
            echo "Error: Python 3.13 is not installed. Please install Python 3.13 first."
            exit 1
        fi
        python3.13 -m venv venv
    fi
    
    source venv/bin/activate
    
    if [ ! -f "venv/updated" ] || [ "requirements.txt" -nt "venv/updated" ]; then
        echo "Installing Python dependencies..."
        pip install -q -r requirements.txt
        touch venv/updated
    fi
    
    cd - > /dev/null
}

check_frontend_requirements() {
    echo "Checking frontend requirements..."
    cd "$FRONTEND_DIR"
    
    if [ ! -d "node_modules" ]; then
        echo "Installing Node dependencies..."
        npm install
    fi
    
    cd - > /dev/null
}

kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)..."
        kill -9 "$pid" 2>/dev/null || true
    fi
}

reset_backend() {
    echo "Resetting backend..."
    kill_port $BACKEND_PORT
    cd "$BACKEND_DIR"
    
    if [ -d "venv" ]; then
        echo "Removing virtual environment..."
        rm -rf venv
    fi
    
    if [ -f "venv/updated" ]; then
        rm -f venv/updated
    fi
    
    cd - > /dev/null
    echo "Backend reset complete"
}

reset_frontend() {
    echo "Resetting frontend..."
    kill_port $FRONTEND_PORT
    cd "$FRONTEND_DIR"
    
    if [ -d "node_modules" ]; then
        echo "Removing node_modules..."
        rm -rf node_modules
    fi
    
    if [ -d "dist" ]; then
        echo "Removing dist directory..."
        rm -rf dist
    fi
    
    cd - > /dev/null
    echo "Frontend reset complete"
}

start_backend() {
    echo "Starting backend server..."
    check_backend_requirements
    cd "$BACKEND_DIR"
    source venv/bin/activate
    export PORT=$BACKEND_PORT
    export HOST=${HOST:-127.0.0.1}
    uvicorn app.main:app --host $HOST --port $BACKEND_PORT --reload
}

start_frontend() {
    echo "Starting frontend server..."
    check_frontend_requirements
    cd "$FRONTEND_DIR"
    export HOST=0.0.0.0
    export PORT=$FRONTEND_PORT
    npm run start
}

start_all() {
    echo "Starting all services..."
    trap "kill_port $BACKEND_PORT; kill_port $FRONTEND_PORT" EXIT
    
    start_backend &
    BACKEND_PID=$!
    sleep 3
    
    start_frontend &
    FRONTEND_PID=$!
    
    wait $BACKEND_PID $FRONTEND_PID
}

stop_services() {
    echo "Stopping services..."
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
    echo "Services stopped"
}

show_status() {
    echo "Service Status:"
    echo "================"
    
    local backend_running=false
    local frontend_running=false
    
    if lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        backend_running=true
        echo "Backend: Running (port $BACKEND_PORT)"
    else
        echo "Backend: Stopped"
    fi
    
    if lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        frontend_running=true
        echo "Frontend: Running (port $FRONTEND_PORT)"
    else
        echo "Frontend: Stopped"
    fi
    
    echo ""
    if $backend_running && $frontend_running; then
        echo "Status: All services running"
    elif $backend_running || $frontend_running; then
        echo "Status: Partially running"
    else
        echo "Status: All services stopped"
    fi
}

docker_up() {
    echo "Starting services with Docker Compose..."
    docker-compose up
}

docker_up_detached() {
    echo "Starting services with Docker Compose (detached)..."
    docker-compose up -d
}

docker_down() {
    echo "Stopping Docker Compose services..."
    docker-compose down
}

# Parse arguments
if [ -z "$1" ]; then
    print_usage
    exit 0
fi
COMMAND=$1
shift

# Parse options first
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            BACKEND_PORT=$2
            shift 2
            ;;
        --host)
            HOST=$2
            shift 2
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        *)
            # If it's a positional argument (not an option), break the loop
            break
            ;;
    esac
done

# Any remaining arguments are positional (e.g., "all" for reset)
REMAINING_ARGS="$@"

case $COMMAND in
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    all)
        start_all
        ;;
    reset)
        TARGET=${REMAINING_ARGS:-all}
        case $TARGET in
            backend)
                reset_backend
                start_backend
                ;;
            frontend)
                reset_frontend
                start_frontend
                ;;
            all)
                reset_backend
                reset_frontend
                start_all
                ;;
            *)
                echo "Unknown reset target: $TARGET"
                print_usage
                exit 1
                ;;
        esac
        ;;
    stop)
        stop_services
        ;;
    status)
        show_status
        ;;
    docker)
        docker_up
        ;;
    docker-up)
        docker_up
        ;;
    docker-up-detached|up)
        docker_up_detached
        ;;
    docker-down|down)
        docker_down
        ;;
    help|--help|-h)
        print_usage
        ;;
    *)
        echo "Unknown command: $COMMAND"
        print_usage
        exit 1
        ;;
esac
