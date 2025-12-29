#!/bin/bash
# Start script for Symmetry Unified Backend

cd "$(dirname "$0")"

# Virtual environment setup
VENV_DIR="venv"

# Check if virtual environment exists, create if not
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip -q

echo "Starting Symmetry Unified Backend..."
echo "Installing dependencies if needed..."
pip install -q -r requirements.txt

echo "Starting FastAPI server..."
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
