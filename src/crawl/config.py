from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import yaml


@dataclass(frozen=True)
class CrawlPolicy:
    max_pages: int
    max_depth: int
    concurrency: int
    request_delay_sec: float
    timeout_sec: int
    user_agent: str
    accept_only_content_types: List[str]
    max_response_bytes: int


@dataclass(frozen=True)
class SourceConfig:
    id: str
    name: str
    base_url: str
    start_urls: List[str]
    allowed_domains: List[str]
    allow_regex: List[str]
    deny_regex: List[str]
    save_regex: List[str]       
    crawl_policy: CrawlPolicy


@dataclass(frozen=True)
class StorageConfig:
    data_dir: str
    raw_html_dir: str
    meta_dir: str
    text_dir: str
    manifest_path: str
    extract_text: bool
    normalize_to_utf8: bool


@dataclass(frozen=True)
class DedupConfig:
    enabled: bool
    drop_fragment: bool
    drop_query: bool
    hash_algorithm: str
    hash_mode: str  


@dataclass(frozen=True)
class AppConfig:
    sources: List[SourceConfig]
    storage: StorageConfig
    dedup: DedupConfig


def _must(d: Dict[str, Any], key: str) -> Any:
    if key not in d:
        raise ValueError(f"Missing config key: {key}")
    return d[key]


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    sources: List[SourceConfig] = []
    for s in _must(raw, "sources"):
        pol = s["crawl_policy"]
        policy = CrawlPolicy(
            max_pages=int(_must(pol, "max_pages")),
            max_depth=int(_must(pol, "max_depth")),
            concurrency=int(_must(pol, "concurrency")),
            request_delay_sec=float(_must(pol, "request_delay_sec")),
            timeout_sec=int(_must(pol, "timeout_sec")),
            user_agent=str(_must(pol, "user_agent")),
            accept_only_content_types=list(_must(pol, "accept_only_content_types")),
            max_response_bytes=int(_must(pol, "max_response_bytes")),
        )

        sources.append(
            SourceConfig(
                id=str(_must(s, "id")),
                name=str(_must(s, "name")),
                base_url=str(_must(s, "base_url")),
                start_urls=list(_must(s, "start_urls")),
                allowed_domains=list(_must(s, "allowed_domains")),
                allow_regex=list(_must(s, "allow_regex")),
                deny_regex=list(_must(s, "deny_regex")),
                save_regex=list(s.get("save_regex", [])),  # NEW
                crawl_policy=policy,
            )
        )

    st = _must(raw, "storage")
    storage = StorageConfig(
        data_dir=str(_must(st, "data_dir")),
        raw_html_dir=str(_must(st, "raw_html_dir")),
        meta_dir=str(_must(st, "meta_dir")),
        text_dir=str(_must(st, "text_dir")),
        manifest_path=str(_must(st, "manifest_path")),
        extract_text=bool(st.get("extract_text", True)),
        normalize_to_utf8=bool(_must(st, "normalize_to_utf8")),
    )

    dd = _must(raw, "deduplication")
    urln = _must(dd, "url_normalization")
    ch = _must(dd, "content_hash")
    dedup = DedupConfig(
        enabled=bool(_must(dd, "enabled")),
        drop_fragment=bool(_must(urln, "drop_fragment")),
        drop_query=bool(_must(urln, "drop_query")),
        hash_algorithm=str(_must(ch, "algorithm")),
        hash_mode=str(_must(ch, "mode")),
    )

    return AppConfig(sources=sources, storage=storage, dedup=dedup)
