"""
Install the spaCy language models the backend needs.

Usage (from symmetry-unified-backend, with the virtualenv active):

    python scripts/install_spacy_models.py            # uses SPACY_MODELS, or the default set
    python scripts/install_spacy_models.py es fr ja   # install specific languages
    python scripts/install_spacy_models.py all        # every supported language
    python scripts/install_spacy_models.py --list     # show what is installed, change nothing

Models that are already installed are skipped, so it is safe to run this on
every start. The same script is used by the Dockerfile, start.sh and CI.
"""

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

# Make "app" importable when this file is run directly as a script.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.spacy_models import (
    SPACY_MODEL_MAP,
    SPACY_MODELS_ENV_VAR,
    resolve_spacy_models,
)


def is_installed(model_name: str) -> bool:
    """spaCy models are regular Python packages, so a package lookup is enough."""
    return importlib.util.find_spec(model_name) is not None


def download(model_name: str) -> bool:
    """Download one model with spaCy's own downloader. Returns True on success."""
    result = subprocess.run(
        [sys.executable, "-m", "spacy", "download", model_name],
        check=False,
    )
    return result.returncode == 0


def print_status() -> None:
    """Print every supported language and whether its model is installed."""
    for language, model_name in sorted(SPACY_MODEL_MAP.items()):
        state = "installed" if is_installed(model_name) else "missing"
        print(f"{language}  {model_name:<18} {state}")


def install(model_names: list[str]) -> list[str]:
    """Install the given models and return the ones that failed."""
    failed: list[str] = []
    for model_name in model_names:
        if is_installed(model_name):
            print(f"{model_name}: already installed", flush=True)
            continue
        print(f"{model_name}: downloading...", flush=True)
        if not download(model_name):
            print(f"{model_name}: download failed", file=sys.stderr)
            failed.append(model_name)
    return failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install the spaCy language models the backend needs."
    )
    parser.add_argument(
        "models",
        nargs="*",
        help=(
            "Language codes or model names, or 'default' / 'all'. "
            f"If omitted, the {SPACY_MODELS_ENV_VAR} environment variable is used."
        ),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Show which supported models are installed and exit.",
    )
    args = parser.parse_args(argv)

    if args.list:
        print_status()
        return 0

    spec = " ".join(args.models) or os.environ.get(SPACY_MODELS_ENV_VAR)
    try:
        model_names = resolve_spacy_models(spec)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    failed = install(model_names)
    if failed:
        print(f"Could not install: {', '.join(failed)}", file=sys.stderr)
        return 1

    print(f"spaCy models ready: {', '.join(model_names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
