# Contributing to Project Symmetry

Thank you for your interest in contributing! This guide covers everything you need
to get started.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Submitting Changes](#submitting-changes)
- [Coding Conventions](#coding-conventions)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](./CODE_OF_CONDUCT.md).
By participating you agree to uphold it.

---

## Getting Started

1. **Fork** the repository and clone your fork locally.
2. Create a feature branch off `develop`:

   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feat/my-feature
   ```

3. Set up the development environment (see below).
4. Make your changes, write tests, and open a Pull Request against `develop`.

---

## Development Setup

### Prerequisites

| Tool | Version |
| ---- | ------- |
| Python | 3.10 – 3.11 |
| Node.js | 18 LTS |
| npm | 9+ |
| Docker | 24+ (optional) |

### Backend

```bash
cd symmetry-unified-backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Copy and edit environment config
cp ../.env.example .env

# Start the API server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd desktop-electron-frontend
npm ci
npm start        # Electron dev mode
# or
npm run dev      # Browser-only (Vite) dev mode
```

### All-in-one (Docker Compose)

```bash
./start.sh docker
```

---

## Running Tests

### Backend (Running Tests)

```bash
cd symmetry-unified-backend
source venv/bin/activate
pytest -v --tb=short                        # all fast tests
pytest -m "not slow and not external"       # CI subset
```

### Linting

```bash
# Python
pip install ruff
ruff check symmetry-unified-backend/
```

---

## Submitting Changes

1. Ensure **all tests pass** before opening a PR.
2. Target the `develop` branch (not `main` — that branch is reserved for releases).
3. Fill in the PR template: describe *what* changed and *why*.
4. One approval from a maintainer is required to merge.
5. Add an entry under `## [Unreleased]` in [`CHANGELOG.md`](./CHANGELOG.md) following the
   existing format.

---

## Coding Conventions

### Python

- PEP 8, 88-char line length (`ruff` is the linter)
- Type hints on all public function signatures
- Pydantic v2 models with `Field` descriptions

### TypeScript / React

- 2-space indentation
- `PascalCase` for components and types, `camelCase` for functions and variables
- Interfaces mirror backend Pydantic models (snake_case field names)

### Git Commits

- Use [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`)
- Keep commits atomic and focused on one change
