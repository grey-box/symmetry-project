# Project Symmetry

Minimal project README for local development and reference.

## What is this

A repository with a Python FastAPI backend in `symmetry-unified-backend` and a frontend in `desktop-electron-frontend`.

## Local setup

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
npm install
npm run dev
```

## Tests

### Backend

```bash
cd symmetry-unified-backend
source venv/bin/activate
python -m pytest -m "not slow and not external" --tb=short
```

### Frontend

```bash
cd desktop-electron-frontend
npm test
```

## Documentation

- `docs/README.md`
- `symmetry-unified-backend/README.md`
- `desktop-electron-frontend/README.md`
