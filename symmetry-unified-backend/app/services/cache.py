import hashlib
import logging
from time import time
from typing import Dict, List, Optional, Tuple
from collections import OrderedDict
from sys import getsizeof

CACHE_LIMIT = 10
TTL_SECONDS = 4000


class ArticleCache:
    def __init__(self, max_size: int = CACHE_LIMIT, ttl: int = TTL_SECONDS):
        self.cache: "OrderedDict[str, Dict]" = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
        self.current_size = 0

    def _get_cache_key(self, key: str) -> str:
        return hashlib.md5(key.encode()).hexdigest()

    def get(self, key: str) -> Tuple[Optional[str], Optional[List[str]]]:
        cache_key = self._get_cache_key(key)
        cached_data = self.cache.get(cache_key)

        if not cached_data:
            logging.info(f"[CACHE MISS] No cache entry for key: {cache_key}")
            return None, None

        if time() - cached_data["timestamp"] > self.ttl:
            self._evict(cache_key, reason="expired")
            return None, None

        self.cache.move_to_end(cache_key)
        logging.info(f"[CACHE HIT] Returning cached data for key: {cache_key}")
        return cached_data["content"], cached_data["languages"]

    def set(self, key: str, content: str, languages: List[str]) -> None:
        cache_key = self._get_cache_key(key)
        item = {
            "content": content,
            "languages": languages,
            "timestamp": time(),
        }
        item_size = getsizeof(item)

        if cache_key in self.cache:
            self.current_size -= getsizeof(self.cache[cache_key])
            self.cache.move_to_end(cache_key)
        elif len(self.cache) >= self.max_size:
            evicted_key, evicted_val = self.cache.popitem(last=False)
            self.current_size -= getsizeof(evicted_val)
            logging.info(f"[CACHE EVICTED] LRU item: {evicted_key}")

        self.cache[cache_key] = item
        self.current_size += item_size
        logging.info(
            f"[CACHE SET] Key: {cache_key} | Size: {len(self.cache)}/{self.max_size}"
        )

    def _evict(self, key: str, reason: str = "manual") -> None:
        if key in self.cache:
            self.current_size -= getsizeof(self.cache[key])
            del self.cache[key]
            logging.info(f"[CACHE {reason.upper()}] Evicted key: {key}")


_article_cache = ArticleCache()


def get_cached_article(title: str) -> Tuple[Optional[str], Optional[List[str]]]:
    return _article_cache.get(title)


def set_cached_article(key: str, content: str, languages: List[str]) -> None:
    _article_cache.set(key, content, languages)
