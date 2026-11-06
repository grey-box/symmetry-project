"""Shared pieces for v2 endpoints that compare texts with the embedding model.

Used by every endpoint that offers an embedding strategy such as
``semantic_similarity`` (LLM vs Wikipedia, LLM vs LLM).
"""

from app.models.v2 import ErrorDetail
from app.services.v2_engines import EngineHandle
from app.services.v2_responses import error_detail
from app.strategies.text import split_sentences

EMBEDDING_ENGINE_ID = "embedding-default"


# The server's embedding model, which serves embedding strategies. model_name
# overrides the default comparison model (for example in tests).
def embedding_engine(model_name: str | None = None) -> EngineHandle:
    from app.models.comparison.registry import DEFAULT_MODEL

    return EngineHandle(
        id=EMBEDDING_ENGINE_ID,
        type="embedding",
        model=model_name or DEFAULT_MODEL,
        provider="local",
    )


# Turns a semantic_similarity result into one row per sentence of the text that was
# compared first. Matched sentences are in details["alignments"] with their score;
# unmatched ones are findings whose confidence is 1 - similarity. Labels follow
# schema section 6: similarity >= threshold is supported, >= partial_threshold is
# partial, else not_found. Each row keeps its closest sentence in the other text;
# evidence is that sentence for supported and partial rows only.
def similarity_rows(
    details: dict,
    findings: list,
    text: str,
    *,
    partial_threshold: float | None,
) -> list[dict]:
    threshold = details["threshold"]
    matched = {a["source_index"]: a for a in details.get("alignments", [])}
    unmatched = iter(f for f in findings if f.label == "no_match_in_target")
    rows = []
    for index, sentence in enumerate(split_sentences(text)):
        if index in matched:
            similarity = matched[index]["score"]
            closest = matched[index]["target_text"]
        else:
            finding = next(unmatched, None)
            if finding is None:
                continue
            similarity = 1.0 - (finding.confidence or 0.0)
            closest = finding.evidence
        similarity = round(min(1.0, max(0.0, similarity)), 4)
        if similarity >= threshold:
            label = "supported"
        elif partial_threshold is not None and similarity >= partial_threshold:
            label = "partial"
        else:
            label = "not_found"
        rows.append(
            {
                "statement": sentence,
                "label": label,
                "confidence": None,
                "similarity": similarity,
                "closest": closest,
                "evidence": closest if label != "not_found" else None,
            }
        )
    return rows


# Maps a pipeline error entry from the embedding model onto the v2 error model.
def embedding_error(
    entry: dict, engine_id: str, details: dict | None = None
) -> ErrorDetail:
    message = str(entry.get("message") or "The embedding model failed.")
    code = entry.get("code")
    if code == "invalid_request":
        return error_detail("invalid_request", message)
    if code != "engine_timeout":
        code = "engine_unavailable"
    return error_detail(code, message, "engine", engine_id=engine_id, details=details)
