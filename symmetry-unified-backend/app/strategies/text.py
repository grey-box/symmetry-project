import re

# Ends a sentence after . ! ? (followed by space), after CJK sentence marks, or at a line break.
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|(?<=[。！？])|\n+")


# Splits text into sentences. Each sentence is an exact piece of the original text,
# so it can be found again by offset. Abbreviations such as "Dr." are split too; pass
# a better splitter to a strategy that needs one.
def split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in _SENTENCE_BREAK.split(text)]
    return [part for part in parts if part]
