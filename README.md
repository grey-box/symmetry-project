<p align="center">
    <img width="200" alt="Grey-box Logo" src="https://www.grey-box.ca/wp-content/uploads/2018/05/logoGREY-BOX.jpg">
</p>

<h1 align="center">Project Symmetry - Cross-Language Wikipedia Article Gap Analysis Tool</h1>

<p align="center">
  <img alt="Project-Symmetry: Cross-Language Wikipedia Article Semantic Analysis Tool"
       src="extras/symmetrydemo2.png">
</p>

<p align="center">
  <strong>A modern semantic translator tool designed to translate, compare, and evaluate the semantic similarity of Wikipedia content across different languages</strong>
</p>

## 🚀 Quick Start

### Prerequisites
- [Node.js](https://nodejs.org/) (v18+)
- [Python](https://www.python.org/) (3.8-3.11)
- [npm](https://www.npmjs.com/)
- [Docker](https://www.docker.com/) (optional, for containerized deployment)
- [Docker Compose](https://docs.docker.com/compose/) (optional)

### Quick Start (Recommended)

The project includes a unified `start.sh` script that handles both local and Docker deployments.

#### Start Everything (Local Development)
```bash
# Start both backend and frontend
./start.sh all

# Start with frontend in development mode
./start.sh all --dev
```

#### Using Docker Compose
```bash
# Start both services in containers (foreground)
./start.sh docker

# Start in background (detached)
./start.sh docker-up

# Stop all containers
./start.sh docker-down
```

#### Individual Services
```bash
# Backend only
./start.sh backend

# Frontend only
./start.sh frontend

# Frontend in development mode
./start.sh frontend --dev
```

#### Reset Services
```bash
# Reset and restart backend
./start.sh reset backend

# Reset and restart frontend
./start.sh reset frontend

# Reset and restart both
./start.sh reset all
```

#### Check Status & Stop
```bash
# Check status of services
./start.sh status

# Stop all running services
./start.sh stop

# Show help
./start.sh help
```

#### Custom Ports and Hosts
```bash
# Start backend on custom port
./start.sh backend --port 9000

# Start backend on custom host
./start.sh backend --host 0.0.0.0

# Start all with custom port
./start.sh all --port 9000
```

### Access Points

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Interactive Swagger UI**: http://localhost:8000/docs

### Manual Installation (Advanced)

#### Backend
```bash
cd symmetry-unified-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

#### Frontend
```bash
cd desktop-electron-frontend

# Install dependencies
yarn install

# Run development
yarn start
```

## 📖 Project Overview

Project Symmetry uses AI to accelerate Wikipedia's translation efforts in less-represented languages (< 1M articles) by analyzing semantic gaps between articles in different languages and providing targeted translations.

The application helps identify critical information lost or added during translation, useful for scenarios without internet access, such as medical documents, government communications, and NGO materials.

Currently focused on Wikipedia content; future expansion to other internet content and AI-powered translation for underrepresented languages.

## 📊 Features

- **🌍 Wikipedia Translation**: Translate articles between languages
- **🔍 Semantic Comparison**: Identify gaps and additions in translations using AI models
- **📊 Gap Analysis**: Detect missing/extra information with color-coded results
- **🎯 Language Support**: Focus on underrepresented languages
- **📝 Structured Articles**: Section-by-section content with citations and references
- **🤖 AI-Powered**: Semantic understanding with models like LaBSE, XLM-RoBERTa
- **📈 Analytics**: Translation quality metrics and structural analysis
- **🧪 Testing**: Comprehensive test suite with 100% pass rate (56 tests)

## 🏗️ Project Structure

```
symmetry-project-202512/
├── symmetry-unified-backend/   # FastAPI backend
│   ├── app/
│   │   ├── ai/               # AI and ML components
│   │   │   ├── semantic_comparison.py
│   │   │   └── translations.py
│   │   ├── models/           # Pydantic v2 models
│   │   ├── routers/          # API route handlers
│   │   │   ├── wiki_articles.py
│   │   │   ├── structured_wiki.py
│   │   │   ├── comparison.py
│   │   │   └── structural_analysis.py
│   │   ├── services/         # Business logic
│   │   │   ├── article_parser.py
│   │   │   ├── cache.py
│   │   │   └── wiki_utils.py
│   │   ├── prompts/          # LLM prompts
│   │   └── main.py
│   ├── tests/                # Test suite
│   └── requirements.txt
├── desktop-electron-frontend/ # Electron + React frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── services/         # API services
│   │   ├── models/           # TypeScript interfaces
│   │   ├── constants/        # Application constants
│   │   ├── context/          # React context
│   │   └── pages/            # Page components
│   └── package.json
└── README.md
```

## 🔧 Installation Guide

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

### Manual Installation

#### Backend
```bash
cd symmetry-unified-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env as needed (LOG_LEVEL, FASTAPI_DEBUG)
```

#### Frontend
```bash
cd desktop-electron-frontend

# Install dependencies
yarn install

# Verify installation
yarn list --depth=0
```

### Running the Application

#### Development Mode
```bash
# Backend (with hot reload)
cd symmetry-unified-backend
source venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd desktop-electron-frontend
yarn start
```

#### Production Mode
```bash
# Backend
cd symmetry-unified-backend
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4

# Frontend - package for distribution
cd desktop-electron-frontend
yarn package
```

## 🤝 Contributing

Thank you for your interest in contributing to Project Symmetry!

### Getting Started

1. Fork the repository
2. Create a feature branch
3. Install dependencies (see Installation Guide)
4. Make your changes
5. Run tests
6. Submit a pull request

### Code Standards

#### Python Backend
- Use PEP 8 style guidelines (88 char max line length)
- 4 spaces for indentation
- Type hints for all functions
- Docstrings for public functions
- PEP 8 naming conventions (snake_case)

#### JavaScript/TypeScript Frontend
- ESLint and Prettier configuration
- 2 spaces for indentation
- Components: PascalCase
- Services/Utilities: camelCase
- Types: PascalCase

### Testing

#### Backend
```bash
cd symmetry-unified-backend
source venv/bin/activate
pytest
```

Test coverage: 60 tests, 97% pass rate

#### Frontend
```bash
cd desktop-electron-frontend
yarn test
```

### Development Workflow

```bash
# Always pull latest changes
git fetch upstream
git rebase upstream/main

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test
cd symmetry-unified-backend && pytest
cd ../desktop-electron-frontend && yarn test

# Commit and push
git add .
git commit -m "feat: description of changes"
git push origin feature/your-feature-name

# Create pull request
gh pr create --title "Feature Title" --body "Description..."
```

### Pull Request Checklist
- [ ] Code follows project standards
- [ ] Tests pass (backend and frontend)
- [ ] Documentation updated
- [ ] No breaking changes (unless documented)
- [ ] Commit messages follow conventional format

## 📚 Documentation

### Main Documentation
- **Installation Guide** - See Installation section above
- **Contributing Guide** - See Contributing section above
- **Backend README** - [symmetry-unified-backend/README.md](symmetry-unified-backend/README.md)
- **Frontend README** - [desktop-electron-frontend/README.md](desktop-electron-frontend/README.md)

### API Documentation
Interactive API documentation available at http://127.0.0.1:8000/docs when backend is running.

### Key API Endpoints

#### Wiki Articles
- `GET /symmetry/v1/wiki/articles` - Fetch Wikipedia article
- `GET /symmetry/v1/wiki/structured-article` - Get structured article with sections, citations, references
- `GET /symmetry/v1/wiki/structured-section` - Get specific section with metadata
- `GET /symmetry/v1/wiki/citation-analysis` - Analyze citations
- `GET /symmetry/v1/wiki/reference-analysis` - Analyze references
- `GET /wiki_translate/source_article` - Get translated article

#### Comparison
- `POST /symmetry/v1/articles/compare` - Compare two articles (semantic comparison)
- `GET /symmetry/v1/comparison/semantic` - Semantic comparison (GET)
- `POST /symmetry/v1/comparison/semantic` - Semantic comparison (POST)
- `GET /symmetry/v1/comparison/translate_text` - Translate text (GET)
- `POST /symmetry/v1/comparison/translate_text` - Translate text (POST)

### Models Management
- `GET /models/translation` - List available translation models
- `GET /models/translation/selected` - Get selected translation model
- `GET /models/translation/select?modelname={name}` - Select translation model
- `GET /models/translation/delete?modelname={name}` - Delete translation model
- `GET /models/translation/import?model={name}&from_huggingface={bool}` - Import translation model
- `GET /models/comparison` - List available comparison models
- `GET /models/comparison/selected` - Get selected comparison model
- `GET /models/comparison/select?modelname={name}` - Select comparison model
- `GET /models/comparison/delete?modelname={name}` - Delete comparison model
- `GET /models/comparison/import?model={name}&from_huggingface={bool}` - Import comparison model

#### Structural Analysis
- `GET /operations/{source_language}/{title}` - Analyze article across 6 languages with quality scoring

## 🧪 Testing

### Backend Testing

Run all tests:
```bash
cd symmetry-unified-backend
pytest
```

Run specific test file:
```bash
pytest tests/test_wiki_articles.py
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

Run with verbose output:
```bash
pytest -v
```

### Test Coverage

- **Total Tests**: 56
- **Passing**: 56 (100%)
- **Test Categories**: Wiki articles, comparison, structured wiki, structural analysis
- **Test Time**: ~5s

### Test Data

Sample article texts in `tests/data/`:
- `obama_A.txt` and `obama_B.txt`: For comparison tests
- `missingno_en.txt` and `missingno_fr.txt`: Multi-language tests

## 🎓 Learning Resources

### Prerequisites

#### Git and GitHub
- [GitHub Guides](https://guides.github.com/)
- [Pro Git Book](https://git-scm.com/book/)

#### Python Development
- [Python Documentation](https://docs.python.org/3/)
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)
- [pytest Documentation](https://docs.pytest.org/)

#### JavaScript/TypeScript Development
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)
- [React Documentation](https://reactjs.org/docs/)
- [Electron Documentation](https://www.electronjs.org/docs)

### Recommended Learning Path

1. **Week 1**: Set up development environment and understand project structure
2. **Week 2**: Study the existing codebase and run the application
3. **Week 3**: Make small contributions (documentation, bug fixes)
4. **Week 4**: Work on a feature under mentorship
5. **Week 5+**: Contribute independently and help others

## 🔍 Areas for Contribution

### High Priority
- **🌍 Translation Improvements**: Add support for more languages, improve accuracy
- **🔍 Semantic Analysis**: Enhance comparison algorithms, add more models
- **🧪 Testing**: Increase test coverage, add integration tests

### Medium Priority
- **🖥️ UI/UX Improvements**: Redesign components, add dark mode
- **⚡ Performance**: Optimize API responses, reduce memory usage
- **📚 Documentation**: Update API documentation, add tutorials

### Low Priority
- **🔧 DevOps**: Set up CI/CD pipeline, add monitoring
- **🎨 Design**: Update icons and logos, improve visual consistency

## 🐛 Troubleshooting

### Backend Issues

#### "python3: command not found"
Edit `start.sh` and change `python3` to `python`.

#### Permission denied on start.sh
```bash
chmod +x start.sh
```

#### Virtual environment issues
Rebuild from scratch:
```bash
deactivate
rm -rf venv/
./start.sh
```

#### Ollama not running for LLM comparison
```bash
ollama serve
# In another terminal:
ollama pull deepseek-r1
```

### Frontend Issues

#### npm install fails
```bash
# Clear cache and reinstall
yarn cache clean
rm -rf node_modules
yarn install
```

#### Port already in use
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

### Platform-Specific Issues

#### Windows
- Add exception in Windows Defender
- Allow connections through Windows Firewall
- Ensure Python and Node.js are in PATH

#### Linux/macOS
- Ensure OpenGL ES 2.0 or higher
- Fix permissions: `chmod +x start.sh`

## 🤝 Community

- **Project Website**: [Project-Symmetry](https://www.grey-box.ca/project-symmetry/)
- **GitHub Issues**: [Report Issues](https://github.com/grey-box/Project-Symmetry-AI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/grey-box/Project-Symmetry-AI/discussions)
- **Design Resources**: [Figma UX](https://www.figma.com/design/yN89gDcV3rdbje70X9RJGL/Project-Symmetry?node-id=199-529&t=MbzAcPzTNmWPFh8w-0)

## 📄 License

This project is licensed under the appropriate license. See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Grey Box**: Project development and maintenance
- **Wikipedia**: Source content and API access
- **Open Source Community**: Libraries and tools

---

**Last Updated**: December 2025  
**Version**: 1.0.0  
**Maintainers**: [grey-box](https://github.com/grey-box)
