from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str, drop_query: bool, drop_fragment: bool) -> str:
    parts = urlsplit(url)
    query = "" if drop_query else parts.query
    fragment = "" if drop_fragment else parts.fragment
    
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, query, fragment))
