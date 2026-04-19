"""Top-level Wikipedia parser (copy of Phase_3.wikipedia_parser).

Kept at project root for easier import by other teams/tools.
"""
from typing import List, Dict, Optional

import re

try:
    import requests
    from bs4 import BeautifulSoup
except Exception:
    raise

# nltk's sent_tokenize if available; otherwise use a regex fallback
try:
    import nltk
    from nltk.tokenize import sent_tokenize
    _NLTK_AVAILABLE = True
except Exception:
    _NLTK_AVAILABLE = False


USER_AGENT = "similarity-prototype-bot/1.0 (https://example.com)"


def fetch_html(url: str, timeout: int = 10) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def filter_trivial_sentences(sentences: List[str], min_words: int = 4) -> List[str]:
    filtered = []
    for sent in sentences:
        word_count = len(sent.split())
        if word_count >= min_words:
            filtered.append(sent)
    return filtered

def get_flat_sentences(url: str, max_paragraphs: Optional[int] = None) -> List[str]:
    parsed = parse_url_to_paragraph_sentences(url, max_paragraphs)
    
    flat = []
    for item in parsed:
        for sentence in item["sentences"]:
            cleaned = clean_sentence(sentence)
            if len(cleaned.split()) >= 4:  # filter trivial
                flat.append(cleaned)
    
    return flat

def clean_sentence(sentence: str) -> str:
    # Remove URLs
    sentence = re.sub(r'http\S+', '', sentence)
    # Remove multiple spaces
    sentence = re.sub(r'\s+', ' ', sentence)
    # Remove coordinates like (12°N 45°E)
    sentence = re.sub(r'\(\d+°[NS].*?\)', '', sentence)
    return sentence.strip()

def extract_paragraphs(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find(id="mw-content-text") or soup.find("div", class_="mw-parser-output")
    if content is None:
        paras = soup.find_all("p")
    else:
        paras = content.find_all("p")

    texts = []
    for p in paras:
        for sup in p.find_all("sup"):
            sup.decompose()
        txt = p.get_text(separator=" ", strip=True)
        if txt and len(txt) > 30:
            texts.append(txt)
    return texts


_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'\(\[])")


def _regex_split_sentences(text: str) -> List[str]:
    t = re.sub(r"\s+", " ", text).strip()
    if not t:
        return []
    parts = _SENT_SPLIT_RE.split(t)
    parts = [p.strip() for p in parts if p and len(p.strip()) > 0]
    return parts


def split_into_sentences(text: str) -> List[str]:
    if _NLTK_AVAILABLE:
        try:
            return sent_tokenize(text)
        except LookupError:
            try:
                nltk.download("punkt", quiet=True)
                return sent_tokenize(text)
            except Exception:
                return _regex_split_sentences(text)
        except Exception:
            return _regex_split_sentences(text)
    else:
        return _regex_split_sentences(text)


def parse_url_to_paragraph_sentences(url: str, max_paragraphs: Optional[int] = None) -> List[Dict[str, List[str]]]:
    html = fetch_html(url)
    paras = extract_paragraphs(html)
    if max_paragraphs is not None:
        paras = paras[:max_paragraphs]

    out = []
    for p in paras:
        sents = split_into_sentences(p)
        out.append({"paragraph": p, "sentences": sents})
    return out


def vectorize_paragraphs_tfidf(paragraphs: List[Dict[str, List[str]]]):
    from Phase_1.vectorizer import Vectorizer

    flat = []
    for p_idx, p in enumerate(paragraphs):
        for s_idx, s in enumerate(p.get("sentences", [])):
            flat.append({"paragraph_index": p_idx, "sentence_index": s_idx, "text": s})

    texts = [f["text"] for f in flat]

    vec = Vectorizer()
    vectors_map = vec.get_vectors(texts)
    vectors = [vectors_map.get(t, []) for t in texts]

    return {
        "vectorizer": vec,
        "vocabulary": vec.vocabulary,
        "flat": flat,
        "vectors": vectors,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python wikipedia_parser.py <wikipedia_url>")
        sys.exit(1)

    url = sys.argv[1]
    results = parse_url_to_paragraph_sentences(url, max_paragraphs=5)
    for i, item in enumerate(results, 1):
        print(f"\nParagraph {i}: {item['paragraph'][:200]}{'...' if len(item['paragraph'])>200 else ''}\n")
        for j, s in enumerate(item["sentences"], 1):
            print(f"  {j}. {s}")
