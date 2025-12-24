from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from .config import SourceConfig


@dataclass
class CompiledSourceRules:
    source: SourceConfig
    allow: List[re.Pattern]
    deny: List[re.Pattern]
    save: List[re.Pattern]   
    domains: set[str]


def compile_rules(sources: List[SourceConfig]) -> List[CompiledSourceRules]:
    compiled: List[CompiledSourceRules] = []
    for s in sources:
        compiled.append(
            CompiledSourceRules(
                source=s,
                allow=[re.compile(x) for x in s.allow_regex],
                deny=[re.compile(x) for x in s.deny_regex],
                save=[re.compile(x) for x in (s.save_regex or [])],  # NEW
                domains=set(s.allowed_domains),
            )
        )
    return compiled


def match_source(url: str, rules: List[CompiledSourceRules]) -> Optional[CompiledSourceRules]:
    host = (urlparse(url).hostname or "").lower()
    for r in rules:
        if host in r.domains:
            return r
    return None


def url_allowed(url: str, r: CompiledSourceRules) -> bool:
    for d in r.deny:
        if d.match(url):
            return False
    if not r.allow:
        return True
    return any(a.match(url) for a in r.allow)


def url_savable(url: str, r: CompiledSourceRules) -> bool:
    
    if not r.save:
        return url_allowed(url, r)
    return any(s.match(url) for s in r.save)
