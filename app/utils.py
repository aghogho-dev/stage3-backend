from slowapi import Limiter
from slowapi.util import get_remote_address

import hashlib
import json

limiter = Limiter(key_func=get_remote_address)


def generate_normalized_cache_key(filters: dict) -> str:
    normalized = {}
    for k,v in filters.items():
        key = str(k).lower()
        if isinstance(v, str):
            normalized[key] = v.strip().lower()
        else:
            normalized[key] = v

    canonical_json = json.dumps(normalized, sort_keys=True)

    return f"query:{hashlib.md5(canonical_json.encode()).hexdigest()}"