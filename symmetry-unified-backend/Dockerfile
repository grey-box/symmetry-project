FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# spaCy models to bake into the image: language codes or model names, comma
# separated, or "default" / "all". Only the files the install script needs are
# copied here so this layer stays cached when the rest of the app changes.
ARG SPACY_MODELS=default
COPY scripts/install_spacy_models.py scripts/
COPY app/__init__.py app/
COPY app/core/__init__.py app/core/spacy_models.py app/core/
RUN python scripts/install_spacy_models.py

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/LaBSE')"

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
