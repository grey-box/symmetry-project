import hashlib
from collections import OrderedDict
from typing import Any, Optional


class RevisionCache:
    def __init__(self, max_size: int = 50):
        self.cache: "OrderedDict[str, Any]" = OrderedDict()
        self.max_size = max_size

    def _key(self, title: str, lang: str, revid: int) -> str:
        raw = f"{lang}.{title}.{revid}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, title: str, lang: str, revid: int) -> Optional[Any]:
        key = self._key(title, lang, revid)
        return self.cache.get(key)

    def set(self, title: str, lang: str, revid: int, value: Any) -> None:
        key = self._key(title, lang, revid)

        if key in self.cache:
            self.cache.move_to_end(key)
        elif len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)

        self.cache[key] = value


revision_cache = RevisionCache()