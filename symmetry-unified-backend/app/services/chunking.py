

def chunk_text(text: str, chunk_size: int = 450, overlap: int = 60) -> list[str]:
    if not text:
        return []

    words = text.split()
    if len(words) <= chunk_size:
        return [" ".join(words)]

    chunks: list[str] = []
    step = max(1, chunk_size - overlap)

    i = 0
    n = len(words)
    while i < n:
        chunk = words[i : i + chunk_size]
        if chunk:
            chunks.append(" ".join(chunk))
        i += step

    return chunks
