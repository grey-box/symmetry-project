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

### Installation
```bash
# Clone the repository
git clone https://github.com/grey-box/Project-Symmetry-AI
cd Project-Symmetry-AI

# Install frontend dependencies
cd ui
npm install

# Setup backend
cd ../backend-fastapi
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run the application
cd ../ui
npm run start
```

For detailed installation instructions, platform-specific guides, and troubleshooting, see [INSTALLATION.md](INSTALLATION.md).

## 📖 Project Overview

Project Symmetry uses AI to accelerate Wikipedia's translation efforts in less-represented languages (< 1M articles) by analyzing semantic gaps between articles in different languages and providing targeted translations.

The application helps identify critical information lost or added during translation, useful for scenarios without internet access, such as medical documents, government communications, and NGO materials.

Currently focused on Wikipedia content; future expansion to other internet content and AI-powered translation for underrepresented languages.

For detailed project objectives, architecture, working principles, and development status, see [guide/SymmetryAI-Guide.md](guide/SymmetryAI-Guide.md).

## 📊 Features

- **🌍 Wikipedia Translation**: Translate articles between languages
- **🔍 Semantic Comparison**: Identify gaps and additions in translations using AI models
- **📊 Gap Analysis**: Detect missing/extra information with color-coded results
- **🎯 Language Support**: Focus on underrepresented languages
- **⚡ FastAPI Backend**: RESTful API with automatic documentation
- **🖥️ Electron Frontend**: Cross-platform desktop application
- **🤖 AI-Powered**: LLM-based semantic understanding with models like LaBSE, XLM-RoBERTa
- **📈 Analytics**: Translation quality metrics and data analytics

## 🏗️ Project Structure

```
Project-Symmetry-AI/
├── backend-fastapi/          # FastAPI backend
│   ├── app/
│   │   ├── main.py           # Main application entry point
│   │   ├── ai/               # AI and ML components
│   │   │   ├── semantic_comparison.py
│   │   │   ├── llm_comparison.py
│   │   │   └── translations.py
│   │   ├── api/              # API endpoints
│   │   │   ├── wiki_article.py
│   │   │   ├── comparison.py
│   │   │   └── cache.py
│   │   ├── model/            # Data models
│   │   │   ├── request.py
│   │   │   └── response.py
│   │   └── prompts/          # AI prompts
├── ui/                       # Electron + React frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   │   ├── TranslationSection.tsx
│   │   │   ├── ComparisonSection.tsx
│   │   │   ├── Navbar.tsx
│   │   │   └── Layout.tsx
│   │   ├── services/         # API services
│   │   │   ├── fetchArticle.ts
│   │   │   ├── translateArticle.ts
│   │   │   └── compareArticles.ts
│   │   ├── models/           # TypeScript interfaces
│   │   ├── constants/        # Application constants
│   │   ├── context/          # React context
│   │   └── pages/            # Page components
├── T5-finetuned/             # Fine-tuned T5 model
├── guide/                    # Project documentation
└── extras/                   # Resources
```

## 📚 Documentation

- **[INSTALLATION.md](INSTALLATION.md)** - Complete setup instructions for all platforms
- **[guide/SymmetryAI-Guide.md](guide/SymmetryAI-Guide.md)** - Comprehensive project overview, architecture, and development details
- **[api-documentation.md](api-documentation.md)** - Complete API reference with examples
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Guidelines for contributing, development workflow, and code standards
- **[LEARN.md](LEARN.md)** - Prerequisites and learning resources for contributors

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

**Last Updated**: November 2024  
**Version**: 1.0.0  
**Maintainers**: [grey-box](https://github.com/grey-box)
