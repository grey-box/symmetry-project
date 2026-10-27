#!/bin/bash

set -e

# Run from the repository root so the relative paths below work no matter
# where the script is called from (including start-windows.cmd).
cd "$(dirname "$0")"

FRONTEND_DIR="desktop-electron-frontend"
BACKEND_DIR="symmetry-unified-backend"
BACKEND_PORT=8000
FRONTEND_PORT=5173
# Seconds to wait for the backend to answer /health before giving up.
BACKEND_START_TIMEOUT=${BACKEND_START_TIMEOUT:-180}

# Git Bash on Windows reports MINGW/MSYS. Windows needs different commands
# for Python, the virtual environment and finding/stopping processes.
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) IS_WINDOWS=true ;;
    *) IS_WINDOWS=false ;;
esac

if $IS_WINDOWS; then
    VENV_ACTIVATE="venv/Scripts/activate"
else
    VENV_ACTIVATE="venv/bin/activate"
fi

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
    docker-up-rebuild  Rebuild and start Docker services
    docker-down     Stop Docker Compose services
    
    help            Show this help message

Options:
    --port          Override backend port (default: 8000)
    --host          Override backend host (default: 127.0.0.1)
    --dev           Start frontend in development mode

Examples:
    $0                          Start backend and frontend
    $0 backend                  Start only backend
    $0 frontend --dev           Start frontend in dev mode
    $0 all --port 9000          Start both on port 9000
    $0 reset backend            Reset and restart backend
    $0 docker-up                Start with Docker Compose (detached)

On Windows, run this script from Git Bash, or use start-windows.cmd from
Command Prompt or PowerShell (it takes the same commands).
EOF
}

# Print the command that runs Python 3.11, or fail if there isn't one.
# Windows installs it as "py -3.11" (the Python launcher), not python3.11.
find_python311() {
    if command -v python3.11 &> /dev/null; then
        echo "python3.11"
    elif $IS_WINDOWS && command -v py &> /dev/null && py -3.11 --version &> /dev/null; then
        echo "py -3.11"
    else
        return 1
    fi
}

check_backend_requirements() {
    echo "Checking backend requirements..."
    cd "$BACKEND_DIR"
    
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment with Python 3.11..."
        if ! PYTHON=$(find_python311); then
            echo "Error: Python 3.11 is not installed. Please install Python 3.11 first."
            exit 1
        fi
        $PYTHON -m venv venv
    fi
    
    source "$VENV_ACTIVATE"
    
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

# Print the IDs of processes listening on a port, one per line.
pids_on_port() {
    local port=$1
    if $IS_WINDOWS; then
        # Windows netstat lines look like:
        #   TCP    127.0.0.1:8000    0.0.0.0:0    LISTENING    12345
        netstat -ano | tr -d '\r' | awk -v suffix=":$port" '
            $1 == "TCP" && $4 == "LISTENING" &&
            substr($2, length($2) - length(suffix) + 1) == suffix { print $5 }
        ' | sort -u
    else
        lsof -ti:"$port" -sTCP:LISTEN 2>/dev/null || true
    fi
}

kill_port() {
    local port=$1
    local pid
    for pid in $(pids_on_port "$port"); do
        echo "Killing process on port $port (PID: $pid)..."
        if $IS_WINDOWS; then
            # /T also stops child processes, such as uvicorn's reloader
            # worker or the Electron window started by electron-forge.
            taskkill //F //T //PID "$pid" > /dev/null 2>&1 || true
        else
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
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

run_backend() {
    cd "$BACKEND_DIR"
    source "$VENV_ACTIVATE"
    export PORT=$BACKEND_PORT
    export HOST=${HOST:-127.0.0.1}
    uvicorn app.main:app --host $HOST --port $BACKEND_PORT --reload
}

run_frontend() {
    cd "$FRONTEND_DIR"
    export HOST=0.0.0.0
    export PORT=$FRONTEND_PORT
    npm run start
}

start_backend() {
    echo "Starting backend server..."
    check_backend_requirements
    run_backend
}

start_frontend() {
    echo "Starting frontend server..."
    check_frontend_requirements
    run_frontend
}

# Wait until the backend answers /health, so the app doesn't open before
# the backend can serve it. Fails if the backend exits or takes too long.
wait_for_backend() {
    local backend_pid=$1
    local host=${HOST:-127.0.0.1}
    [ "$host" = "0.0.0.0" ] && host=127.0.0.1
    local url="http://$host:$BACKEND_PORT/health"
    local waited=0

    echo "Waiting for the backend at $url ..."
    until curl -sf -o /dev/null "$url"; do
        if ! kill -0 "$backend_pid" 2>/dev/null; then
            echo "Error: the backend stopped before it was ready. See the output above."
            return 1
        fi
        if [ "$waited" -ge "$BACKEND_START_TIMEOUT" ]; then
            echo "Error: the backend did not answer within $BACKEND_START_TIMEOUT seconds."
            return 1
        fi
        sleep 1
        waited=$((waited + 1))
    done
    echo "Backend is ready."
}

start_all() {
    echo "Starting all services..."
    # A server left over from an earlier run would answer the health check
    # below in place of the new one, so refuse to start on a busy port.
    local port
    for port in $BACKEND_PORT $FRONTEND_PORT; do
        if [ -n "$(pids_on_port $port)" ]; then
            echo "Error: port $port is already in use. Run '$0 stop' first, or check what is using it."
            exit 1
        fi
    done

    # Install anything missing first, so the backend wait below only covers
    # server startup and not a first-time pip or npm install.
    check_backend_requirements
    check_frontend_requirements

    # Stop both servers when this script exits, including after Ctrl+C.
    trap "kill_port $BACKEND_PORT; kill_port $FRONTEND_PORT" EXIT
    trap "exit 130" INT TERM
    
    echo "Starting backend server..."
    run_backend &
    BACKEND_PID=$!
    wait_for_backend $BACKEND_PID
    
    echo "Starting frontend server..."
    run_frontend &
    FRONTEND_PID=$!
    
    # Closing the app window ends the frontend, and the EXIT trap then stops
    # the backend as well.
    wait $FRONTEND_PID
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
    
    if [ -n "$(pids_on_port $BACKEND_PORT)" ]; then
        backend_running=true
        echo "Backend: Running (port $BACKEND_PORT)"
    else
        echo "Backend: Stopped"
    fi
    
    if [ -n "$(pids_on_port $FRONTEND_PORT)" ]; then
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

docker_up_rebuild() {
    echo "Rebuilding Docker images..."
    docker-compose build
    echo "Starting services with Docker Compose (detached)..."
    docker-compose up -d
}

docker_down() {
    echo "Stopping Docker Compose services..."
    docker-compose down
}

# Parse arguments. With no command, start everything (as the help says).
COMMAND=${1:-all}
if [ $# -gt 0 ]; then
    shift
fi

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
    docker-up-rebuild|rebuild)
        docker_up_rebuild
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
