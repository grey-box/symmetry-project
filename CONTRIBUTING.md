# 🤝 Project Symmetry Contributing Guide

Thank you for your interest in contributing to Project Symmetry! This guide will help you understand how to contribute to the project effectively.

## 📋 Table of Contents

- [🎯 Getting Started](#-getting-started)
- [📝 Development Workflow](#-development-workflow)
- [🔧 Code Standards](#-code-standards)
- [🧪 Testing Guidelines](#-testing-guidelines)
- [📋 Pull Request Process](#-pull-request-process)
- [🏗️ Project Structure](#-project-structure)
- [🔍 Areas for Contribution](#-areas-for-contribution)
- [📞 Community Guidelines](#-community-guidelines)
- [🎓 Learning Resources](#-learning-resources)

## 🎯 Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Git**: Latest version installed
- **Node.js**: Version 18+ (LTS recommended)
- **Python**: Version 3.8 - 3.11
- **Code Editor**: VS Code, IntelliJ, or your preferred IDE
- **Basic Knowledge**: 
  - JavaScript/TypeScript for frontend
  - Python for backend
  - RESTful APIs
  - Git basics

### First-Time Setup

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork locally
git clone https://github.com/YOUR_USERNAME/Project-Symmetry-AI
cd Project-Symmetry-AI

# 3. Add the original repository as upstream
git remote add upstream https://github.com/grey-box/Project-Symmetry-AI

# 4. Create a feature branch
git checkout -b feature/your-feature-name

# 5. Install dependencies
cd ui && npm install
cd ../backend-fastapi && python -m venv venv
source venv/bin/activate && pip install -r requirements.txt
```

### Verify Setup

```bash
# Test backend
cd app && python -c "import main; print('✅ Backend setup successful')"

# Test frontend
cd ../../ui && npm run build
```

## 📝 Development Workflow

### 1. Choose an Area to Contribute

Browse through these areas:

- **🌍 Translation Features**: Improve translation algorithms
- **🔍 Semantic Analysis**: Enhance comparison algorithms
- **🖥️ UI/UX**: Frontend improvements and design
- **⚡ Performance**: Backend optimization
- **📚 Documentation**: Improve guides and API docs
- **🧪 Testing**: Add test coverage
- **🔧 DevOps**: CI/CD and deployment

### 2. Find or Create an Issue

```bash
# Check existing issues
gh issue list --state open

# Create a new issue
gh issue create --title "Your Feature Request" --body "Detailed description..."
```

### 3. Development Process

```bash
# Always pull latest changes from upstream
git fetch upstream
git rebase upstream/main

# Create a new branch for your feature
git checkout -b feature/your-feature-name

# Make your changes
# ... code changes ...

# Test your changes
cd backend-fastapi && pytest
cd ../ui && npm test

# Commit your changes
git add .
git commit -m "feat: add new translation feature"

# Push to your fork
git push origin feature/your-feature-name

# Create a pull request
gh pr create --title "Your Feature Title" --body "Detailed description..."
```

## 🔧 Code Standards

### Python Backend Standards

#### Code Style
```python
# Use PEP 8 style guidelines
# Maximum line length: 88 characters
# Use 4 spaces for indentation

# Example function
def translate_article(
    title: str, 
    target_language: str, 
    source_language: str = "en"
) -> dict:
    """
    Translate a Wikipedia article to the target language.
    
    Args:
        title: Article title to translate
        target_language: Target language code (e.g., 'fr', 'es')
        source_language: Source language code (default: 'en')
    
    Returns:
        Dictionary containing translation results
    """
    try:
        # Implementation
        pass
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise TranslationError(f"Failed to translate {title}")
```

#### Import Organization
```python
# Standard library imports
import os
import json
from typing import Dict, List, Optional

# Third-party imports
import fastapi
import wikipediaapi
from sentence_transformers import SentenceTransformer

# Local imports
from app.model.request import TranslationRequest
from app.model.response import TranslationResponse
from app.api.cache import get_cached_translation
```

#### Error Handling
```python
class TranslationError(Exception):
    """Custom exception for translation errors."""
    pass

def safe_translation(func):
    """Decorator for safe translation operations."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except wikipediaapi.WikipediaException as e:
            logger.error(f"Wikipedia API error: {e}")
            raise TranslationError("Failed to fetch article from Wikipedia")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise TranslationError("Translation service unavailable")
    return wrapper
```

### JavaScript/TypeScript Frontend Standards

#### Code Style
```typescript
// Use ESLint and Prettier configuration
// Maximum line length: 100 characters
// Use 2 spaces for indentation

// Example component
interface TranslationProps {
  articleTitle: string;
  targetLanguage: string;
  onTranslationComplete: (result: TranslationResult) => void;
}

const TranslationSection: React.FC<TranslationProps> = ({
  articleTitle,
  targetLanguage,
  onTranslationComplete,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [translation, setTranslation] = useState<string>('');

  const handleTranslate = async () => {
    try {
      setIsLoading(true);
      const result = await translateArticle(articleTitle, targetLanguage);
      setTranslation(result.translated_article);
      onTranslationComplete(result);
    } catch (error) {
      console.error('Translation failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="translation-section">
      <h2>Translation</h2>
      <button 
        onClick={handleTranslate}
        disabled={isLoading}
      >
        {isLoading ? 'Translating...' : 'Translate'}
      </button>
      {translation && (
        <div className="translation-result">
          {translation}
        </div>
      )}
    </div>
  );
};
```

#### File Naming Conventions
```typescript
// Components: PascalCase
// TranslationSection.tsx
// ComparisonResults.tsx
// SettingsPanel.tsx

// Services: camelCase
// translationService.ts
// articleService.ts
// apiClient.ts

// Utilities: camelCase
// validators.ts
// formatters.ts
// helpers.ts

// Types: PascalCase
// TranslationTypes.ts
// ApiTypes.ts
// ComponentTypes.ts
```

## 🧪 Testing Guidelines

### Backend Testing

#### Unit Tests
```python
# tests/test_translation.py
import pytest
from app.ai.translations import translate_article
from app.model.request import TranslationRequest

def test_successful_translation():
    """Test successful article translation."""
    request = TranslationRequest(
        title="Machine Learning",
        target_language="fr"
    )
    
    result = translate_article(request)
    
    assert result.translated_article is not None
    assert len(result.translated_article) > 0
    assert "apprentissage automatique" in result.translated_article.lower()

def test_translation_invalid_language():
    """Test translation with invalid language code."""
    request = TranslationRequest(
        title="Test",
        target_language="invalid_lang"
    )
    
    with pytest.raises(TranslationError):
        translate_article(request)

def test_translation_empty_title():
    """Test translation with empty title."""
    request = TranslationRequest(
        title="",
        target_language="fr"
    )
    
    with pytest.raises(ValueError):
        translate_article(request)
```

#### Integration Tests
```python
# tests/test_api_integration.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_article_endpoint():
    """Test the get_article endpoint."""
    response = client.get("/get_article?title=Machine%20Learning")
    
    assert response.status_code == 200
    data = response.json()
    assert "sourceArticle" in data
    assert "articleLanguages" in data
    assert isinstance(data["articleLanguages"], list)

def test_translate_article_endpoint():
    """Test the translate_article endpoint."""
    response = client.get("/wiki_translate/source_article?title=Machine%20Learning&language=fr")
    
    assert response.status_code == 200
    data = response.json()
    assert "translated_article" in data
    assert isinstance(data["translated_article"], str)
```

### Frontend Testing

#### Component Tests
```typescript
// tests/TranslationSection.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TranslationSection } from '../components/TranslationSection';
import { translateArticle } from '../services/translationService';

jest.mock('../services/translationService');

describe('TranslationSection', () => {
  const mockOnComplete = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders translation section', () => {
    render(
      <TranslationSection
        articleTitle="Test Article"
        targetLanguage="fr"
        onTranslationComplete={mockOnComplete}
      />
    );

    expect(screen.getByText('Translation')).toBeInTheDocument();
    expect(screen.getByText('Translate')).toBeInTheDocument();
  });

  it('calls translate function when button is clicked', async () => {
    (translateArticle as jest.Mock).mockResolvedValue({
      translated_article: 'Contenu traduit'
    });

    render(
      <TranslationSection
        articleTitle="Test Article"
        targetLanguage="fr"
        onTranslationComplete={mockOnComplete}
      />
    );

    fireEvent.click(screen.getByText('Translate'));

    await waitFor(() => {
      expect(translateArticle).toHaveBeenCalledWith('Test Article', 'fr');
    });
  });
});
```

#### API Service Tests
```typescript
// tests/services/translationService.test.ts
import { translateArticle } from '../services/translationService';
import { TranslationRequest } from '../models/TranslationRequest';

jest.mock('axios');

describe('TranslationService', () => {
  const mockRequest: TranslationRequest = {
    title: 'Machine Learning',
    targetLanguage: 'fr'
  };

  it('successfully translates article', async () => {
    const mockResponse = {
      data: {
        translated_article: 'Apprentissage automatique'
      }
    };

    (require('axios').get as jest.Mock).mockResolvedValue(mockResponse);

    const result = await translateArticle('Machine Learning', 'fr');

    expect(result.translated_article).toBe('Apprentissage automatique');
  });

  it('handles API errors', async () => {
    (require('axios').get as jest.Mock).mockRejectedValue(new Error('API Error'));

    await expect(translateArticle('Test', 'fr')).rejects.toThrow('API Error');
  });
});
```

## 📋 Pull Request Process

### Creating a Pull Request

1. **Ensure your code is up-to-date**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests and linting**
   ```bash
   # Backend
   cd backend-fastapi && pytest && flake8 app/
   
   # Frontend
   cd ui && npm run lint && npm run test
   ```

3. **Create a descriptive pull request**
   ```bash
   gh pr create --title "feat: add French translation support" \
                --body "Adds comprehensive French translation support with improved accuracy metrics. Fixes #123."
   ```

### Pull Request Template

```markdown
## Description
Brief description of the changes and why they are needed.

## Changes Made
- [ ] Added French translation support
- [ ] Improved translation accuracy metrics
- [ ] Added unit tests for new functionality
- [ ] Updated documentation

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Performance tested

## Breaking Changes
- None

## Related Issues
Closes #123
Related to #456

## Screenshots (if applicable)
![Screenshot of new feature](link-to-screenshot)
```

### Review Process

1. **Automated Checks**
   - CI/CD pipeline must pass
   - All tests must pass
   - Code quality checks must pass

2. **Manual Review**
   - Code follows project standards
   - Documentation is updated
   - Changes are well-tested
   - No breaking changes (unless documented)

3. **Review Response**
   - Address all review comments
   - Update tests if needed
   - Respond to each comment individually

## 🏗️ Project Structure

### Backend Structure
```
backend-fastapi/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── ai/                     # AI and ML components
│   │   ├── __init__.py
│   │   ├── semantic_comparison.py
│   │   ├── llm_comparison.py
│   │   └── translations.py
│   ├── api/                    # API endpoints
│   │   ├── __init__.py
│   │   ├── wiki_article.py
│   │   ├── comparison.py
│   │   └── cache.py
│   ├── model/                  # Data models
│   │   ├── __init__.py
│   │   ├── request.py
│   │   └── response.py
│   ├── prompts/                # AI prompts
│   │   ├── first_pass.txt
│   │   └── second_pass.txt
│   └── test/                   # Tests
│       ├── __init__.py
│       ├── test_main.py
│       └── test_ai.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

### Frontend Structure
```
ui/
├── src/
│   ├── components/             # React components
│   │   ├── TranslationSection.tsx
│   │   ├── ComparisonSection.tsx
│   │   ├── Navbar.tsx
│   │   └── Layout.tsx
│   ├── services/               # API services
│   │   ├── fetchArticle.ts
│   │   ├── translateArticle.ts
│   │   └── compareArticles.ts
│   ├── models/                 # TypeScript interfaces
│   │   ├── FetchArticleRequest.ts
│   │   ├── FetchArticleResponse.ts
│   │   ├── TranslateArticleRequest.ts
│   │   └── TranslateArticleResponse.ts
│   ├── constants/              # Application constants
│   │   └── AppConstants.ts
│   ├── context/                # React context
│   │   └── AppContext.tsx
│   ├── pages/                  # Page components
│   │   ├── Home.tsx
│   │   └── Settings.tsx
│   └── utils/                  # Utility functions
│       ├── validators.ts
│       └── formatters.ts
├── package.json
├── tsconfig.json
└── vite.config.ts
```

### Key Files and Components

#### Backend Files

- **Main Application**: [`backend-fastapi/app/main.py`](../backend-fastapi/app/main.py)
- **Semantic Comparison**: [`backend-fastapi/app/ai/semantic_comparison.py`](../backend-fastapi/app/ai/semantic_comparison.py)
- **LLM Comparison**: [`backend-fastapi/app/ai/llm_comparison.py`](../backend-fastapi/app/ai/llm_comparison.py)
- **Translation Service**: [`backend-fastapi/app/ai/translations.py`](../backend-fastapi/app/ai/translations.py)
- **Wiki Article API**: [`backend-fastapi/app/api/wiki_article.py`](../backend-fastapi/app/api/wiki_article.py)
- **Comparison API**: [`backend-fastapi/app/api/comparison.py`](../backend-fastapi/app/api/comparison.py)

#### Frontend Files

- **Main Application**: [`ui/src/main.ts`](../ui/src/main.ts)
- **Translation Section**: [`ui/src/components/TranslationSection.tsx`](../ui/src/components/TranslationSection.tsx)
- **Comparison Section**: [`ui/src/components/ComparisonSection.tsx`](../ui/src/components/ComparisonSection.tsx)
- **Fetch Article Service**: [`ui/src/services/fetchArticle.ts`](../ui/src/services/fetchArticle.ts)
- **Translate Article Service**: [`ui/src/services/translateArticle.ts`](../ui/src/services/translateArticle.ts)
- **App Constants**: [`ui/src/constants/AppConstants.ts`](../ui/src/constants/AppConstants.ts)

### API Integration

The frontend uses [axios](https://axios-http.com/docs/intro) for API calls structured through service modules. The main functions define endpoints and handle input/output structures defined in TypeScript interfaces.

**Key API Endpoints:**

- `get_article` - Fetch source article and available languages
- `translate/targetArticle` - Get translated article
- `comparison/semantic_comparison` - Compare articles semantically

**Configuration:**

- API URLs and host/port defined in [`AppConstants.ts`](../ui/src/constants/AppConstants.ts)
- Request/response models defined in TypeScript interfaces
- Error handling and loading states managed through React context

## 🔍 Areas for Contribution

### High Priority

- **🌍 Translation Improvements**
  - Add support for more languages
  - Improve translation accuracy
  - Optimize translation speed

- **🔍 Semantic Analysis**
  - Enhance comparison algorithms
  - Add more comparison models
  - Improve gap detection accuracy

- **🧪 Testing**
  - Increase test coverage
  - Add integration tests
  - Implement end-to-end testing

### Medium Priority

- **🖥️ UI/UX Improvements**
  - Redesign components
  - Add dark mode
  - Improve accessibility

- **⚡ Performance**
  - Optimize API responses
  - Reduce memory usage
  - Improve loading times

- **📚 Documentation**
  - Update API documentation
  - Add more tutorials
  - Improve installation guides

### Low Priority

- **🔧 DevOps**
  - Set up CI/CD pipeline
  - Add monitoring
  - Improve deployment process

- **🎨 Design**
  - Update icons and logos
  - Improve visual consistency
  - Add animations

## 📞 Community Guidelines

### Code of Conduct

- **Be respectful**: Treat everyone with respect and professionalism
- **Be inclusive**: Welcome contributors from all backgrounds
- **Be constructive**: Provide helpful feedback and suggestions
- **Be patient**: Understand that everyone learns at different paces

### Communication Channels

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For general discussions and questions
- **Email**: For private matters (contact@grey-box.ca)
- **Project Website**: [Project-Symmetry](https://www.grey-box.ca/project-symmetry/)

### Getting Help

1. **Search existing issues** before creating a new one
2. **Use descriptive titles** for issues and pull requests
3. **Provide detailed information** about your problem
4. **Be patient** for responses (typically within 24-48 hours)

### Recognition

Contributors will be recognized in:

- **README.md**: Special thanks section
- **Contributors list**: Automatic tracking via GitHub
- **Release notes**: For significant contributions

## 🎓 Learning Resources

### Prerequisites

#### Git and GitHub

- [GitHub Guides](https://guides.github.com/)
- [Pro Git Book](https://git-scm.com/book/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)

#### Python Development

- [Python Documentation](https://docs.python.org/3/)
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)
- [pytest Documentation](https://docs.pytest.org/)

#### JavaScript/TypeScript Development

- [TypeScript Documentation](https://www.typescriptlang.org/docs/)
- [React Documentation](https://reactjs.org/docs/)
- [Electron Documentation](https://www.electronjs.org/docs)

### Project-Specific Learning

#### Understanding the Codebase
```bash
# Explore the backend structure
cd backend-fastapi
find . -name "*.py" | head -20

# Explore the frontend structure
cd ui
find . -name "*.tsx" | head -20

# Check the API endpoints
cd backend-fastapi/app
grep -r "app\." main.py
```

#### Running in Development Mode
```bash
# Backend development
cd backend-fastapi
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend development
cd ui
npm run dev

# Testing both together
# Terminal 1: Backend
# Terminal 2: Frontend
```

### Recommended Learning Path

1. **Week 1**: Set up development environment and understand project structure
2. **Week 2**: Study the existing codebase and run the application
3. **Week 3**: Make small contributions (documentation, bug fixes)
4. **Week 4**: Work on a feature under mentorship
5. **Week 5+**: Contribute independently and help others

---

**Contributing Guide Version**: 1.0.0  
**Last Updated**: November 2024  
**Maintainers**: [grey-box](https://github.com/grey-box)

## 📄 License

By contributing to Project Symmetry, you agree that your contributions will be licensed under the project's license. See the [LICENSE](LICENSE) file for details.
