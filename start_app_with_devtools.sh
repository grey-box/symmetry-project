#!/bin/bash

# Project Symmetry AI - Application Startup Script with DevTools
# This script starts the application with devtools enabled for development

set -e  # Exit on any error

echo "🚀 Project Symmetry AI - Starting with DevTools"
echo "================================================"

# Function to kill processes on different ports
kill_processes() {
    echo "🔪 Killing existing processes..."
    
    # Log existing node/npm processes before killing
    echo "  🔍 Existing node/npm processes before cleanup:"
    ps aux | grep -E "(node|npm)" | grep -v grep || echo "    No node/npm processes found"
    echo ""
    
    # Kill processes on port 8000 (backend)
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
        echo "  ⚠️  Killing backend server on port 8000..."
        pkill -f "python.*main.py" || true
        pkill -f "uvicorn.*app.main" || true
        sleep 2
    fi
    
    # Kill processes on port 5173 (frontend dev server)
    if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null ; then
        echo "  ⚠️  Killing frontend dev server on port 5173..."
        pkill -f "vite" || true
        pkill -f "npm.*start" || true
        sleep 2
    fi
    
    # Kill any remaining npm/node processes - BUT BE MORE SPECIFIC
    echo "  ⚠️  Cleaning up project-specific node processes..."
    
    # Only kill node/npm processes that are related to this project
    # by looking for processes in the current directory tree
    echo "    Targeting processes in current project directory..."
    
    # Kill node processes that are in this project directory
    pkill -f "node.*$(pwd)" || true
    pkill -f "npm.*$(pwd)" || true
    
    # Also kill common frontend build tools if they're in our project
    pkill -f "vite.*$(pwd)" || true
    pkill -f "webpack.*$(pwd)" || true
    
    echo "  ✅ Project-specific processes killed"
    
    # Log remaining node/npm processes after cleanup
    echo "  🔍 Remaining node/npm processes after cleanup:"
    ps aux | grep -E "(node|npm)" | grep -v grep || echo "    No node/npm processes found"
    echo ""
}

# Function to setup Python environment
setup_python_env() {
    echo "🐍 Setting up Python environment..."
    
    cd symmetry-unified-backend
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "  📦 Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    echo "  🔄 Activating virtual environment..."
    source venv/bin/activate
    
    # Install dependencies using venv's pip
    echo "  📦 Installing Python dependencies..."
    ./venv/bin/pip install -r requirements.txt
    
    # Install PyInstaller if not already installed
    if ! ./venv/bin/pip show pyinstaller >/dev/null 2>&1; then
        echo "  📦 Installing PyInstaller..."
        ./venv/bin/pip install pyinstaller
    fi
    
    echo "  ✅ Python environment setup complete"
}

# Function to build Python executable
build_python_executable() {
    echo "🔨 Building Python executable..."
    
    cd app
    
    # Build with PyInstaller
    pyinstaller -F main.py
    
    echo "  ✅ Python executable built"
}

# Function to setup frontend
setup_frontend() {
    echo "🌐 Setting up frontend..."
    
    cd ../../desktop-electron-frontend
    
    # Install dependencies
    echo "  📦 Installing Node.js dependencies..."
    npm install
    
    echo "  ✅ Frontend setup complete"
}

# Function to start the application with devtools
start_application_with_devtools() {
    echo "🚀 Starting application with DevTools enabled..."
    
    # Set development environment variable
    export NODE_ENV=development
    
    # Start backend in background
    echo "  🔧 Starting backend server..."
    cd ../symmetry-unified-backend/app
    # Get the absolute path to the backend directory
    BACKEND_DIR=$(cd .. && pwd)
    # Create a temporary script with proper PYTHONPATH and virtual environment activation
    cat > temp_backend_run.sh << EOF
#!/bin/bash
cd $(pwd)
source ${BACKEND_DIR}/venv/bin/activate
export PYTHONPATH="${BACKEND_DIR}:\${PYTHONPATH}"
python main.py
EOF
    chmod +x temp_backend_run.sh
    # Use relative path
    nohup ./temp_backend_run.sh > ${BACKEND_DIR}/backend.log 2>&1 &
    BACKEND_PID=$!
    echo "  ✅ Backend started (PID: $BACKEND_PID)"
    
    # Wait for backend to start
    echo "  ⏳ Waiting for backend to start..."
    sleep 5
    
    # Start frontend with devtools
    echo "  🌐 Starting frontend server with DevTools..."
    echo " We are in $(pwd)"
    cd ../../desktop-electron-frontend
    nohup npm run start > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "  ✅ Frontend started with DevTools (PID: $FRONTEND_PID)"
    
    # Display status
    echo ""
    echo "🎉 Application started successfully with DevTools!"
    echo "=================================================="
    echo "📊 Backend:  http://localhost:8000"
    echo "📊 Frontend: http://localhost:5173"
    echo "🔧 DevTools: Enabled (Electron DevTools will open automatically)"
    echo "📊 Logs:"
    echo "   - Backend: backend.log"
    echo "   - Frontend: frontend.log"
    echo ""
    echo "🔧 To stop the application:"
    echo "   pkill -f 'python.*main.py'"
    echo "   pkill -f 'npm.*start.*$(pwd)'"
    echo "   pkill -f 'vite.*$(pwd)'"
    echo ""
    echo "   💡 For safer process management, use:"
    echo "   pkill -f 'python.*main.py'  # Backend only"
    echo "   pkill -f 'npm.*start.*Project-Symmetry-AI'  # Frontend only"
    echo ""
    echo "📋 Process IDs:"
    echo "   - Backend: $BACKEND_PID"
    echo "   - Frontend: $FRONTEND_PID"
    echo ""
    echo "💡 DevTools Tips:"
    echo "   - Press F12 or Ctrl+Shift+I to open DevTools manually"
    echo "   - Use Ctrl+Shift+J to open DevTools console"
    echo "   - DevTools will open automatically in development mode"
}

# Main execution
main() {
    echo "🗓️  $(date)"
    echo ""
    
    # Step 1: Kill existing processes
    kill_processes
    
    # Step 2: Setup Python environment
    setup_python_env
    
    # Step 3: Build Python executable
    echo "  🔨 Building Python executable..."
    build_python_executable
    
    # Step 4: Setup frontend
    setup_frontend
    
    # Step 5: Start application with devtools
    start_application_with_devtools
}

# Run main function
main