import hashlib
import json
from typing import Optional, Dict, Any
from app.core.logging import logger

# In-memory LRU-style cache for classifications
_CACHE: Dict[str, Dict[str, Any]] = {}


def generate_cache_key(lead_summary: str, sector_version: str) -> str:
    """Generates unique hash key for lead summary and active sector version."""
    content = f"{lead_summary.strip().lower()}|{sector_version}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_cached_classification(cache_key: str) -> Optional[Dict[str, Any]]:
    return _CACHE.get(cache_key)


def set_cached_classification(cache_key: str, result: Dict[str, Any]) -> None:
    # Limit cache size to 5000 items
    if len(_CACHE) > 5000:
        # Pop earliest key
        oldest_key = next(iter(_CACHE))
        _CACHE.pop(oldest_key, None)
    _CACHE[cache_key] = result


def clear_classification_cache() -> None:
    _CACHE.clear()
    logger.info("Classification cache cleared.")
