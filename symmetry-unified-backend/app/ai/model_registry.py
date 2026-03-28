"""
Central registry of supported sentence-transformer models.

Import COMPARISON_MODELS from here instead of redeclaring the list
in individual modules.
"""

COMPARISON_MODELS: list[str] = [
    "sentence-transformers/LaBSE",
    "xlm-roberta-base",
    "multi-qa-distilbert-cos-v1",
    "multi-qa-MiniLM-L6-cos-v1",
    "multi-qa-mpnet-base-cos-v1",
]

DEFAULT_MODEL = "sentence-transformers/LaBSE"
