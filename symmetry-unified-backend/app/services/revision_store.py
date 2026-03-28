import json
import re
from pathlib import Path
from typing import List, Optional

from app.models.revision import Revision

BASE_DIR = Path(__file__).resolve().parents[1]
REVISION_STORE_DIR = BASE_DIR / "data" / "revision_snapshots"


def _safe_name(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "_", text)
    return text[:120]


def _snapshot_path(title: str, lang: str, revid: int) -> Path:
    safe_title = _safe_name(title)
    lang_dir = REVISION_STORE_DIR / lang
    lang_dir.mkdir(parents=True, exist_ok=True)
    return lang_dir / f"{safe_title}.{revid}.json"


def save_revision_snapshot(title: str, lang: str, revision: Revision) -> None:
    path = _snapshot_path(title, lang, revision.revid)
    path.write_text(
        json.dumps(revision.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_revision_snapshot(title: str, lang: str, revid: int) -> Optional[Revision]:
    path = _snapshot_path(title, lang, revid)
    if not path.exists():
        return None

    data = json.loads(path.read_text(encoding="utf-8"))
    return Revision.model_validate(data)


def list_revision_snapshots(title: str, lang: str) -> List[Revision]:
    safe_title = _safe_name(title)
    lang_dir = REVISION_STORE_DIR / lang
    if not lang_dir.exists():
        return []

    snapshots: List[Revision] = []
    for path in sorted(lang_dir.glob(f"{safe_title}.*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        snapshots.append(Revision.model_validate(data))

    return snapshots