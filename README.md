# Project Symmetry - Cross-Language Wikipedia Article Gap Analysis Tool

![Grey-box Logo](https://www.grey-box.ca/wp-content/uploads/2018/05/logoGREY-BOX.jpg)

![CI](https://github.com/grey-box/symmetry-project/actions/workflows/ci.yml/badge.svg) ![Release](https://github.com/grey-box/symmetry-project/actions/workflows/release.yml/badge.svg) ![Latest Release](https://img.shields.io/github/v/release/grey-box/symmetry-project)

![Project-Symmetry: Cross-Language Wikipedia Article Semantic Analysis Tool](extras/symmetrydemo2.png)

**A semantic analysis tool that compares Wikipedia articles across languages section-by-section and paragraph-by-paragraph to identify content gaps, missing information, and added content.**

---

## Prerequisites

- [Node.js](https://nodejs.org/) (v18+)
- [Python](https://www.python.org/) (3.8-3.11)
- [npm](https://www.npmjs.com/) / [yarn](https://yarnpkg.com/)
- [Docker](https://www.docker.com/) (optional, for containerized deployment)

## Start Everything (Local Development)

```bash
# Start both backend and frontend
./start.sh all

# Start with frontend in development mode
./start.sh all --dev
```

## Using Docker Compose

```bash
./start.sh docker       # Foreground
./start.sh docker-up    # Detached
./start.sh docker-down  # Stop
```

### Backend

```bash
cd symmetry-unified-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd desktop-electron-frontend
yarn install
yarn start
```

## Access Points

- **Frontend**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Tech Stack

- **Frontend**: Electron 26 + React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui
- **Backend**: Python + FastAPI + sentence-transformers + spaCy + MarianMT
- **Comparison Engine**: LaBSE sentence embeddings (cosine similarity) + Levenshtein distance for disambiguation

---

## Section Comparison (Primary)

- `POST /symmetry/v1/articles/compare-sections` - Compare two Wikipedia articles section-by-section with paragraph-level diffs

## Structured Wiki

- `GET /symmetry/v1/wiki/structured-article` - Parse article into sections/citations/references

## Legacy Comparison

- `POST /symmetry/v1/articles/compare` - Plain-text semantic comparison

## Models Management

- `GET /models/comparison` - List comparison models

---

## Testing

```bash
cd symmetry-unified-backend
source venv/bin/activate
pytest              # Run all tests
pytest -v           # Verbose
pytest --cov=app    # With coverage
```

---

## CI/CD

The project uses GitHub Actions for continuous integration and automated releases.

### Workflows

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| **CI** (`.github/workflows/ci.yml`) | Push/PR to `main` or `develop` | Runs backend tests, builds frontend web bundle, builds & smoke-tests frontend Docker image, runs docker-compose integration |
| **Release** (`.github/workflows/release.yml`) | Push to `main` | Runs full CI → bumps version (semver) → creates git tag → creates GitHub release → publishes Docker images to GHCR |

---

## Docker Images

Released images are available from GHCR:

```bash
# Pull specific version
docker pull ghcr.io/grey-box/symmetry-project/backend:1.1.0
docker pull ghcr.io/grey-box/symmetry-project/frontend:1.1.0

# Pull latest
docker pull ghcr.io/grey-box/symmetry-project/backend:latest
docker pull ghcr.io/grey-box/symmetry-project/frontend:latest
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Install dependencies (see Quick Start)
4. Make changes and run tests
5. Use [Conventional Commits](https://www.conventionalcommits.org/) for your commit messages
6. Submit a pull request to `develop`
7. After review, PRs are merged to `develop`, then promoted to `main` for release

---

## Community

- **Project Website**: [Project-Symmetry](https://www.grey-box.ca/project-symmetry/)
- **GitHub Issues**: [Report Issues](https://github.com/grey-box/Project-Symmetry-AI/issues)
- **Design Resources**: [Figma UX](https://www.figma.com/design/yN89gDcV3rdbje70X9RJGL/Project-Symmetry?node-id=199-529&t=MbzAcPzTNmWPFh8w-0)

---

## License

This project is licensed under the appropriate license. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **Grey Box**: Project development and maintenance
- **Wikipedia**: Source content and API access
- **Open Source Community**: Libraries and tools

---

**Last Updated**: March 2026
**Version**: 2.0.0
**Maintainers**: [grey-box](https://github.com/grey-box)
