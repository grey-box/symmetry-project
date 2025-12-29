# 🔧 Project Symmetry Installation Guide

This guide provides detailed instructions for setting up Project Symmetry on different operating systems. Follow these steps to get the application running on your machine.

## 📋 Prerequisites

Before starting the installation, ensure you have the following tools installed:

### System Requirements
- **Operating System**: Windows 10+, Ubuntu 20.04+, or macOS 10.15+
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: Minimum 2GB free space
- **Internet Connection**: Required for downloading dependencies

### Software Requirements
- **Node.js**: Version 18.0 or higher (LTS recommended)
- **Python**: Version 3.8 - 3.11 (NLP library requirements prevent 3.12)
- **npm**: Version 8.0 or higher (comes with Node.js)
- **Git**: Latest version

### Platform-Specific Requirements
- **Windows**: ConPTY support (Windows 10 version 1809 or higher)
- **Ubuntu**: OpenGL ES 2.0 or higher
- **macOS**: OpenGL ES 2.0 or higher

## 🚀 Installation Steps

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/grey-box/Project-Symmetry-AI
cd Project-Symmetry-AI

# Create a dedicated workspace (optional but recommended)
mkdir -p ~/workspace/project-symmetry
cp -r * ~/workspace/project-symmetry/
cd ~/workspace/project-symmetry
```

### Step 2: Install Frontend Dependencies

```bash
# Navigate to the UI directory
cd ui

# Install Node.js dependencies
npm install

# Verify installation
npm list --depth=0
```

**Troubleshooting npm install:**
```bash
# If you encounter permission issues
npm install --no-optional

# If you want to use a specific Node.js version
nvm use 18
npm install

# Clear npm cache and reinstall
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Step 3: Setup Backend Environment

```bash
# Navigate to the backend directory
cd ../backend-fastapi

# Create a Python virtual environment
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### Step 4: Install Python Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install required packages
pip install -r requirements.txt

# Verify installation
pip list
```

**Optional: Install development dependencies**
```bash
# Install development tools
pip install pytest black flake8 mypy

# Install PyInstaller for building executables
pip install pyinstaller
```

### Step 5: Test the Installation

```bash
# Test the backend
cd app
python -c "import main; print('Backend imports successful')"

# Test the frontend
cd ../../ui
npm run test  # If tests are configured
```

## 🖥️ Running the Application

### Development Mode

#### Backend
```bash
# From backend-fastapi directory (with venv activated)
cd app
python -m app.main

# Or using uvicorn (recommended for development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
# From ui directory
npm run start

# Or for development with hot reload
npm run dev
```

### Production Mode

#### Backend as Service
```bash
# Install the backend as a service
cd app
pyinstaller -F main.py --name symmetry-backend

# Run the generated executable
./dist/symmetry-backend
```

#### Frontend as Desktop Application
```bash
# Package the Electron application
cd ../../ui
npm run package

# The packaged application will be in the 'out' directory
```

## 📱 Platform-Specific Instructions

### Windows Installation

```bash
# PowerShell (Administrator)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# Command Prompt
cd Project-Symmetry-AI
cd backend-fastapi
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Test installation
cd app
python main.py
```

**Windows-specific issues:**
- **Windows Defender**: May flag the application as suspicious. Add an exception.
- **Windows Firewall**: Allow connections on ports 8000 (backend) and 3000 (frontend).
- **Path Issues**: Ensure Python and Node.js are added to PATH.

### Linux (Ubuntu) Installation

```bash
# Update system packages
sudo apt update
sudo apt upgrade

# Install system dependencies
sudo apt install python3-pip python3-venv nodejs npm git

# Clone and install
git clone https://github.com/grey-box/Project-Symmetry-AI
cd Project-Symmetry-AI
cd backend-fastapi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up desktop shortcut (optional)
cat > ~/Desktop/Project-Symmetry.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Project Symmetry
Exec=/home/$(whoami)/Project-Symmetry-AI/ui/node_modules/.bin/electron
Terminal=false
Icon=/home/$(whoami)/Project-Symmetry-AI/extras/symmetrydemo.png
Categories=Development;Utility;
EOF
chmod +x ~/Desktop/Project-Symmetry.desktop
```

### macOS Installation

```bash
# Using Homebrew (recommended)
brew install node python3 git

# Clone and install
git clone https://github.com/grey-box/Project-Symmetry-AI
cd Project-Symmetry-AI
cd backend-fastapi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create launch script
cat > ~/bin/symmetry-start << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/../backend-fastapi"
source venv/bin/activate
cd app
python -m app.main &
cd ../../ui
npm run start &
EOF
chmod +x ~/bin/symmetry-start
```

## 🔧 Building Executables

### Python Backend Executable

```bash
# From backend-fastapi/app directory
cd app

# Clean previous builds
rm -rf build dist *.spec

# Build executable
pyinstaller -F main.py --name symmetry-backend --onefile --windowed --icon=../extras/symmetrydemo.png

# Test the executable
./dist/symmetry-backend
```

**Advanced PyInstaller options:**
```bash
# Include hidden imports
pyinstaller -F --hidden-import=fastapi --hidden-import=uvicorn main.py

# Add data files
pyinstaller --add-data "../extras:extras" main.py

# Create debug build
pyinstaller -F --debug main.py
```

### Electron Frontend Executable

```bash
# From ui directory
cd ui

# Clean previous builds
rm -rf out dist

# Build for specific platform
npm run package

# For cross-platform builds, install electron-builder
npm install -D electron-builder
npx electron-builder --publish=never
```

**Platform-specific builds:**
```bash
# Windows
npm run package:win

# macOS
npm run package:mac

# Linux
npm run package:linux
```

## 🐛 Troubleshooting

### Common Issues

#### Python Virtual Environment Issues
```bash
# Re-create virtual environment
cd backend-fastapi
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Node.js/npm Issues
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Use specific Node.js version
nvm install 18
nvm use 18
```

#### Port Already in Use
```bash
# Find and kill processes using ports
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

#### Permission Issues
```bash
# macOS/Linux: Fix permissions
chmod +x start_app_with_devtools.sh
chmod +x restart_app.sh

# Windows: Run as Administrator
```

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Backend Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# Frontend Configuration
FRONTEND_PORT=3000
ELECTRON_DEV=true

# API Keys (if needed)
WIKIPEDIA_API_KEY=your_api_key_here
OPENAI_API_KEY=your_openai_key_here
```

### Testing the Installation

```bash
# Backend API test
curl -X GET "http://localhost:8000/get_article?title=Test"

# Frontend test (if running)
curl -X GET "http://localhost:3000"

# Python imports test
cd backend-fastapi
python -c "
import sys
sys.path.append('.')
from app.main import app
print('Backend imports successful')
"

# Node.js imports test
cd ui
npm run test  # If configured
```

## 📚 Additional Resources

### Documentation
- **[📖 Project Guide](guide/SymmetryAI-Guide.md)** - Comprehensive project overview
- **[📡 API Documentation](api-documentation.md)** - Complete API reference
- **[🤝 Contributing Guide](CONTRIBUTING.md)** - Guidelines for contributors
- **[🎓 Learning Resources](LEARN.md)** - Prerequisites and learning materials

### Community Support
- **GitHub Issues**: [Report Issues](https://github.com/grey-box/Project-Symmetry-AI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/grey-box/Project-Symmetry-AI/discussions)
- **Project Website**: [Project-Symmetry](https://www.grey-box.ca/project-symmetry/)

### Related Tools
- **Python Virtual Environments**: [venv Documentation](https://docs.python.org/3/library/venv.html)
- **Node.js Package Manager**: [npm Documentation](https://docs.npmjs.com/)
- **Electron Framework**: [Electron Documentation](https://www.electronjs.org/docs)
- **FastAPI Framework**: [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

**Installation Guide Version**: 1.0.0  
**Last Updated**: November 2024  
**Maintainers**: [grey-box](https://github.com/grey-box)
