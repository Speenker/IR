===== docker-compose.yml =====
services:
  mongodb:
    image: mongo:8.0
    container_name: mongodb
    ports:
      - "27017:27017"
    volumes:
      - mongo-data:/data/db
    restart: unless-stopped

volumes:
  mongo-data:


===== configs/sources.yaml =====
sources:
  - id: "city_news_yaroslavl"
    name: "Городские новости (Ярославль)"
    base_url: "https://city-news.ru"
    start_urls:
      - "https://city-news.ru/articles/"
      - "https://city-news.ru/news/"
    allowed_domains:
      - "city-news.ru"
      - "www.city-news.ru"
    allow_regex:
      - "^https?://(www\\.)?city-news\\.ru/articles/?$"
      - "^https?://(www\\.)?city-news\\.ru/news/.*"
      - "^https?://(www\\.)?city-news\\.ru/article/.*"
      - "^https?://(www\\.)?city-news\\.ru/publikatsii/.*"
    save_regex:
      - "^https?://(www\\.)?city-news\\.ru/news/.*"
      - "^https?://(www\\.)?city-news\\.ru/article/.*"
      - "^https?://(www\\.)?city-news\\.ru/publikatsii/.*"
    deny_regex:
      - ".*#.*"
    crawl_policy:
      max_pages: 60000
      max_depth: 10
      concurrency: 30
      request_delay_sec: 0.02
      timeout_sec: 30
      user_agent: "MAI-IR-Labs/1.0 (educational crawler; contact: your_email@example.com)"
      accept_only_content_types: ["text/html"]
      max_response_bytes: 700000

  - id: "kovrovskie_vesti_kovrov"
    name: "Ковровские вести (Ковров)"
    base_url: "https://www.xn--b1aaalbpdjc1bbxpfp.xn--p1ai"
    start_urls:
      - "https://www.xn--b1aaalbpdjc1bbxpfp.xn--p1ai/allnews/"
      - "https://www.xn--b1aaalbpdjc1bbxpfp.xn--p1ai/allnews/page/2/"
      - "https://www.xn--b1aaalbpdjc1bbxpfp.xn--p1ai/allnews/page/10/"
      - "https://www.xn--b1aaalbpdjc1bbxpfp.xn--p1ai/allnews/page/50/"
      - "https://www.xn--b1aaalbpdjc1bbxpfp.xn--p1ai/allnews/page/100/"
      - "https://www.xn--b1aaalbpdjc1bbxpfp.xn--p1ai/allnews/page/200/"
      - "https://www.xn--b1aaalbpdjc1bbxpfp.xn--p1ai/allnews/page/400/"
      - "https://www.xn--b1aaalbpdjc1bbxpfp.xn--p1ai/allnews/page/700/"
      - "https://www.xn--b1aaalbpdjc1bbxpfp.xn--p1ai/allnews/page/900/"
      - "https://www.xn--b1aaalbpdjc1bbxpfp.xn--p1ai/allnews/page/1083/"

    allowed_domains:
      - "www.xn--b1aaalbpdjc1bbxpfp.xn--p1ai"
      - "xn--b1aaalbpdjc1bbxpfp.xn--p1ai"
    allow_regex:
      # лента "Все новости" + пагинация (это критично, иначе фронтир не раскроется)
      - "^https?://(www\\.)?xn--b1aaalbpdjc1bbxpfp\\.xn--p1ai/allnews(/page/\\d+/)?/?$"
      # карточки материалов вида /29588-....html [attached_file:1]
      - "^https?://(www\\.)?xn--b1aaalbpdjc1bbxpfp\\.xn--p1ai/\\d+-[^/]+\\.html$"
    save_regex:
      - "^https?://(www\\.)?xn--b1aaalbpdjc1bbxpfp\\.xn--p1ai/\\d+-[^/]+\\.html$"  # карточка новости [attached_file:1]
    deny_regex:
      - ".*#.*"
      - ".*\\.(jpg|jpeg|png|gif|webp|svg|mp4|mp3|zip|rar)$"
      # PDF можно тоже отрезать (если не хочешь его качать вообще)
      - ".*\\.pdf$"
    crawl_policy:
      # тут можно ставить высокий лимит, сайт большой
      max_pages: 60000
      max_depth: 30
      # лайтово (у тебя уже были 403 на других доменах)
      concurrency: 10
      request_delay_sec: 0.2
      timeout_sec: 30
      user_agent: "MAI-IR-Labs/1.0 (educational crawler; contact: your_email@example.com)"
      accept_only_content_types: ["text/html"]
      max_response_bytes: 700000


  - id: "zelenograd_staroekrukovo"
    name: "Интернет-газета района Старое Крюково (Зеленоград)"
    base_url: "https://staroekrukovo.ru"
    start_urls:
      - "https://staroekrukovo.ru/news/allnews/"   # правильная лента [web:418]
    allowed_domains:
      - "staroekrukovo.ru"
      - "www.staroekrukovo.ru"
    allow_regex:
      - "^https?://(www\\.)?staroekrukovo\\.ru/news/.*"
    save_regex:
      # сохраняем только карточки новостей, не страницы allnews-пагинации
      - "^https?://(www\\.)?staroekrukovo\\.ru/news/(?!allnews/).*"  # пример новости [web:433]
    deny_regex:
      - ".*#.*"
    crawl_policy:
      max_pages: 35000
      max_depth: 15
      concurrency: 30
      request_delay_sec: 0.02
      timeout_sec: 30
      user_agent: "MAI-IR-Labs/1.0 (educational crawler; contact: your_email@example.com)"
      accept_only_content_types: [ "text/html" ]
      max_response_bytes: 700000


  - id: "zelenograd_silino"
    name: "Наше Силино (Зеленоград) — статьи (/articles/...)"
    base_url: "https://nashesilino.ru"
    start_urls:
      - "https://nashesilino.ru/articles/allnews/?SECTION_CODE=allnews"          # лента [web:427]
      - "https://nashesilino.ru/articles/allnews/?SECTION_CODE=allnews&PAGEN_1=1"
      - "https://nashesilino.ru/articles/allnews/?SECTION_CODE=allnews&PAGEN_1=50"
      - "https://nashesilino.ru/articles/allnews/?SECTION_CODE=allnews&PAGEN_1=500"
      - "https://nashesilino.ru/articles/allnews/?SECTION_CODE=allnews&PAGEN_1=1905"  # глубокая страница [web:730]
    allowed_domains:
      - "nashesilino.ru"
      - "www.nashesilino.ru"
    allow_regex:
      # всё под /articles/ (и ленты, и карточки любых разделов)
      - "^https?://(www\\.)?nashesilino\\.ru/articles/.*"
    save_regex:
      # карточка: /articles/<section>/<slug> (пример: moscow/...) [web:736]
      - "^https?://(www\\.)?nashesilino\\.ru/articles/[a-z0-9_-]+/[a-z0-9_-]+/?$"
    deny_regex:
      - ".*#.*"
      - ".*\\?(?!SECTION_CODE=[a-z0-9_-]+(&PAGEN_1=\\d+)?$|show_news=\\d{6}(&SECTION_CODE=[a-z0-9_-]+)?(&PAGEN_1=\\d+)?$).*"
      - ".*\\.(jpg|jpeg|png|gif|webp|svg|mp4|mp3|pdf|zip|rar)$"
    crawl_policy:
      max_pages: 60000
      max_depth: 25
      concurrency: 10
      request_delay_sec: 0.25
      timeout_sec: 30
      user_agent: "MAI-IR-Labs/1.0 (educational crawler; contact: your_email@example.com)"
      accept_only_content_types: [ "text/html" ]
      max_response_bytes: 700000


  - id: "vladnews_vladivostok"
    name: "VladNews (Владивосток) — новости"
    base_url: "https://vladnews.ru"
    start_urls:
      - "https://vladnews.ru/"       # главная лента [web:509]
      - "https://vladnews.ru/archive" # архив новостей [web:614]
    allowed_domains:
      - "vladnews.ru"
      - "www.vladnews.ru"
    allow_regex:
      - "^https?://(www\\.)?vladnews\\.ru/.*"
    save_regex:
      # карточка новости: /YYYY-MM-DD/<id>/<slug> [web:608]
      - "^https?://(www\\.)?vladnews\\.ru/\\d{4}-\\d{2}-\\d{2}/\\d+/[^/?#]+/?$"
    deny_regex:
      - ".*#.*"
      - ".*\\.(jpg|jpeg|png|gif|webp|svg|mp4|mp3|pdf|zip|rar)$"
    crawl_policy:
      max_pages: 60000
      max_depth: 20
      concurrency: 20
      request_delay_sec: 0.2
      timeout_sec: 30
      user_agent: "MAI-IR-Labs/1.0 (educational crawler; contact: your_email@example.com)"
      accept_only_content_types: [ "text/html" ]
      max_response_bytes: 700000



  - id: "newsroom24_nnov"
    name: "Newsroom24 (Нижний Новгород) — новости"
    base_url: "https://newsroom24.ru"
    start_urls:
      - "https://newsroom24.ru/news/?PAGEN_1=1"
      - "https://newsroom24.ru/news/zhizn/?PAGEN_1=1"        # [web:576]
      - "https://newsroom24.ru/news/criminal/?PAGEN_1=1"     # [web:573]
      - "https://newsroom24.ru/news/transport/?PAGEN_1=1"
      - "https://newsroom24.ru/news/sport/?PAGEN_1=1"
      - "https://newsroom24.ru/news/technologies/?PAGEN_1=1"
    allowed_domains:
      - "newsroom24.ru"
      - "www.newsroom24.ru"
    allow_regex:
      - "^https?://(www\\.)?newsroom24\\.ru/news/.*"
    save_regex:
      - "^https?://(www\\.)?newsroom24\\.ru/news/[a-z0-9_-]+/\\d{4}/news_\\d+/?$"  # пример статьи [web:514]
      - "^https?://(www\\.)?newsroom24\\.ru/news/[a-z0-9_-]+/\\d+/?$"
    deny_regex:
      - ".*#.*"
    crawl_policy:
      max_pages: 60000
      max_depth: 20
      concurrency: 30
      request_delay_sec: 0.02
      timeout_sec: 30
      user_agent: "MAI-IR-Labs/1.0 (educational crawler; contact: your_email@example.com)"
      accept_only_content_types: [ "text/html" ]
      max_response_bytes: 700000

  - id: "serpuhov_admin"
    name: "Администрация Серпухова — /novosti (лента) + /news (карточки)"
    base_url: "https://serpuhov.ru"
    start_urls:
      - "https://serpuhov.ru/novosti/?PAGEN_2=1"
    allowed_domains:
      - "serpuhov.ru"
      - "www.serpuhov.ru"
    allow_regex:
      - "^https?://(www\\.)?serpuhov\\.ru/novosti/.*"   # листаем ленту [web:658]
      - "^https?://(www\\.)?serpuhov\\.ru/news/.*"      # карточки [web:648]
    save_regex:
      - "^https?://(www\\.)?serpuhov\\.ru/news/[a-z0-9_-]+/?$"  # карточка [web:648]
    deny_regex:
      - ".*#.*"
      # запрещаем любые query на карточках (а на /novosti/ пусть будут любые)
      - "^https?://(www\\.)?serpuhov\\.ru/news/[^?]+\\?.*$"
      - ".*\\.(jpg|jpeg|png|gif|webp|svg|mp4|mp3|pdf|zip|rar)$"
    crawl_policy:
      max_pages: 60000
      max_depth: 30
      concurrency: 10
      request_delay_sec: 0.25
      timeout_sec: 30
      user_agent: "MAI-IR-Labs/1.0 (educational crawler; contact: your_email@example.com)"
      accept_only_content_types: [ "text/html" ]
      max_response_bytes: 700000



storage:
  data_dir: "data"
  raw_html_dir: "data/raw_html"
  meta_dir: "data/meta"
  extract_text: false
  text_dir: "data/text"
  manifest_path: "data/manifest.csv"
  normalize_to_utf8: true

deduplication:
  enabled: true
  url_normalization:
    drop_fragment: true
    drop_query: false
  content_hash:
    algorithm: "sha256"
    mode: "text"


===== requirements.txt =====
aiohttp==3.10.11
PyYAML==6.0.2
beautifulsoup4==4.12.3
charset-normalizer==3.4.0
motor==3.6.0
pymongo==4.9.2


===== scripts/crawl.py =====
import asyncio
import logging
import sys

from src.crawl.config import load_config
from src.crawl.crawler import Crawler


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main() -> None:
    cfg = load_config("configs/sources.yaml")
    crawler = Crawler(cfg)
    await crawler.run()


if __name__ == "__main__":
    setup_logging()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)


===== scripts/corpus_stats.py =====
import csv
import json
import statistics
from pathlib import Path


RAW_DIR = Path("data/raw_html")
TEXT_DIR = Path("data/text")
MANIFEST = Path("data/manifest.csv")
OUT_JSON = Path("data/corpus_stats.json")


def _safe_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def main() -> None:
    raw_sizes = []
    text_sizes = []
    per_source = {}

    missing_raw = 0
    missing_text = 0
    total_rows = 0

    with MANIFEST.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            total_rows += 1
            doc_id = (row.get("doc_id") or "").strip()
            source_id = (row.get("source_id") or "unknown").strip()

            if not doc_id:
                continue

            per_source[source_id] = per_source.get(source_id, 0) + 1

            raw_path = RAW_DIR / f"{doc_id}.html"
            text_path = TEXT_DIR / f"{doc_id}.txt"

            rs = _safe_size(raw_path)
            if rs == 0:
                missing_raw += 1
            raw_sizes.append(rs)

            ts = _safe_size(text_path)
            if ts == 0:
                missing_text += 1
            text_sizes.append(ts)

    def summarize(sizes):
        sizes_nonzero = [x for x in sizes if x > 0]
        if not sizes_nonzero:
            return {
                "count_nonzero": 0,
                "sum_bytes": 0,
                "avg_bytes": 0,
                "median_bytes": 0,
                "min_bytes": 0,
                "max_bytes": 0,
            }
        return {
            "count_nonzero": len(sizes_nonzero),
            "sum_bytes": sum(sizes_nonzero),
            "avg_bytes": int(sum(sizes_nonzero) / len(sizes_nonzero)),
            "median_bytes": int(statistics.median(sizes_nonzero)),
            "min_bytes": min(sizes_nonzero),
            "max_bytes": max(sizes_nonzero),
        }

    stats = {
        "manifest_rows": total_rows,
        "documents_total": sum(per_source.values()),
        "per_source": dict(sorted(per_source.items(), key=lambda kv: kv[0])),
        "raw_html": summarize(raw_sizes),
        "text": summarize(text_sizes),
        "missing_raw_files": missing_raw,
        "missing_text_files": missing_text,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    # короткий вывод в консоль для отчёта
    print("Documents:", stats["documents_total"])
    print("Per source:", stats["per_source"])
    print("RAW sum MB:", round(stats["raw_html"]["sum_bytes"] / (1024 * 1024), 2))
    print("RAW avg KB:", round(stats["raw_html"]["avg_bytes"] / 1024, 2))
    print("TEXT sum MB:", round(stats["text"]["sum_bytes"] / (1024 * 1024), 2))
    print("TEXT avg KB:", round(stats["text"]["avg_bytes"] / 1024, 2))
    print("Wrote:", str(OUT_JSON))


if __name__ == "__main__":
    main()


===== scripts/extract_text.py =====
import csv
import os
from pathlib import Path

from bs4 import BeautifulSoup


RAW_DIR = Path("data/raw_html")
TEXT_DIR = Path("data/text")
MANIFEST = Path("data/manifest.csv")


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # выкидываем мусор
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # основной текст
    txt = soup.get_text(separator=" ", strip=True)
    return txt


def main() -> None:
    TEXT_DIR.mkdir(parents=True, exist_ok=True)

    done = 0
    skipped = 0
    missing_raw = 0

    with MANIFEST.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            doc_id = row.get("doc_id")
            if not doc_id:
                continue

            out_path = TEXT_DIR / f"{doc_id}.txt"
            if out_path.exists() and out_path.stat().st_size > 0:
                skipped += 1
                continue

            raw_path = RAW_DIR / f"{doc_id}.html"
            if not raw_path.exists():
                missing_raw += 1
                continue

            html = raw_path.read_text(encoding="utf-8", errors="ignore")
            text = html_to_text(html)

            out_path.write_text(text, encoding="utf-8", newline="\n")
            done += 1

            if done % 500 == 0:
                print(f"Extracted {done} texts, skipped {skipped}, missing_raw {missing_raw}")

    print(f"DONE. Extracted={done}, skipped_existing={skipped}, missing_raw={missing_raw}")


if __name__ == "__main__":
    main()

===== src/crawl/config.py =====
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
    save_regex: List[str]          # NEW: что сохраняем в корпус
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
    hash_mode: str  # "text" or "html"


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

===== scripts/robot.py =====
import argparse
import asyncio
import logging
import sys

from src.robot.config import load_robot_config
from src.robot.robot import Robot


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to robot YAML config")
    args = ap.parse_args()

    cfg = load_robot_config(args.config)
    robot = Robot(cfg)
    await robot.run()


if __name__ == "__main__":
    setup_logging()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)


===== src/crawl/crawler.py =====
from __future__ import annotations

import csv
import os
import asyncio
import logging
from dataclasses import dataclass
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from .config import AppConfig
from .fetcher import fetch_html
from .rules import compile_rules, match_source, url_allowed, url_savable
from .storage import Storage
from .text_extract import extract_text_from_html
from .urlnorm import normalize_url

log = logging.getLogger("crawler")


@dataclass(frozen=True)
class QueueItem:
    url: str
    depth: int


class Crawler:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.rules = compile_rules(cfg.sources)

        self.storage = Storage(
            raw_html_dir=cfg.storage.raw_html_dir,
            text_dir=cfg.storage.text_dir,
            meta_dir=cfg.storage.meta_dir,
            manifest_path=cfg.storage.manifest_path,
            extract_text=cfg.storage.extract_text,
        )

        self._queue: asyncio.Queue[QueueItem] = asyncio.Queue()
        self._url_seen: set[str] = set()
        self._text_hash_seen: set[str] = set()
        self._lock = asyncio.Lock()

        self._doc_id = 0
        self._saved_per_source: dict[str, int] = {s.id: 0 for s in cfg.sources}
        self._max_per_source: dict[str, int] = {s.id: s.crawl_policy.max_pages for s in cfg.sources}
        self._total_target = sum(s.crawl_policy.max_pages for s in cfg.sources)

    def _resume_from_manifest(self) -> None:
        """
        Восстанавливает состояние по data/manifest.csv:
        - продолжает doc_id с максимального существующего
        - восстанавливает счетчики per_source
        - добавляет уже скачанные URL в _url_seen
        - добавляет sha256_text в _text_hash_seen (если есть в манифесте)
        """
        path = self.cfg.storage.manifest_path
        if not os.path.exists(path):
            log.info("No manifest.csv found, starting fresh.")
            return

        max_doc_id = 0
        per_source: dict[str, int] = {}
        url_count = 0
        hash_count = 0

        with open(path, "r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            # если файл пустой/битый, DictReader может быть без fieldnames
            if not r.fieldnames:
                return

            for row in r:
                try:
                    doc_id = int(row.get("doc_id", "0") or "0")
                    max_doc_id = max(max_doc_id, doc_id)
                except ValueError:
                    continue

                source_id = (row.get("source_id") or "").strip()
                if source_id:
                    per_source[source_id] = per_source.get(source_id, 0) + 1

                # В _url_seen кладем и url и final_url, нормализуя так же, как в краулере
                for key in ("url", "final_url"):
                    u = (row.get(key) or "").strip()
                    if u:
                        nu = normalize_url(u, self.cfg.dedup.drop_query, self.cfg.dedup.drop_fragment)
                        self._url_seen.add(nu)
                        url_count += 1

                sha = (row.get("sha256_text") or "").strip()
                if sha:
                    self._text_hash_seen.add(sha)
                    hash_count += 1

        # продолжить doc_id и счетчики
        self._doc_id = max_doc_id

        # перенесем per_source в текущую структуру (учитываем новые источники, которых раньше не было)
        for sid, cnt in per_source.items():
            self._saved_per_source[sid] = cnt

        log.info(
            "RESUME: manifest=%s max_doc_id=%s per_source=%s url_seen_added=%s text_hashes_added=%s",
            path, max_doc_id, self._saved_per_source, url_count, hash_count
        )


    async def run(self) -> None:
        self._resume_from_manifest()

        for s in self.cfg.sources:
            for u in s.start_urls:
                nu = normalize_url(u, self.cfg.dedup.drop_query, self.cfg.dedup.drop_fragment)
                await self._enqueue_if_new(nu, depth=0)

        concurrency = max(s.crawl_policy.concurrency for s in self.cfg.sources)
        ua = self.cfg.sources[0].crawl_policy.user_agent

        conn = aiohttp.TCPConnector(limit=concurrency)
        async with aiohttp.ClientSession(headers={"User-Agent": ua}, connector=conn) as session:
            workers = [asyncio.create_task(self._worker(i, session)) for i in range(concurrency)]
            await self._queue.join()
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

        log.info("Done. Saved total=%s. Per source=%s", self._doc_id, self._saved_per_source)

    async def _enqueue_if_new(self, url: str, depth: int) -> None:
        async with self._lock:
            if url in self._url_seen:
                return
            self._url_seen.add(url)
        await self._queue.put(QueueItem(url=url, depth=depth))

    def _source_reached_limit(self, source_id: str) -> bool:
        return self._saved_per_source.get(source_id, 0) >= self._max_per_source.get(source_id, 0)

    async def _worker(self, wid: int, session: aiohttp.ClientSession) -> None:
        while True:
            item = await self._queue.get()
            try:
                await self._process_one(item, session)
            finally:
                self._queue.task_done()

    async def _process_one(self, item: QueueItem, session: aiohttp.ClientSession) -> None:
        # если корпус уже собран — просто быстро вычищаем очередь
        if self._doc_id >= self._total_target:
            return

        r = match_source(item.url, self.rules)
        if r is None:
            return

        if item.depth > r.source.crawl_policy.max_depth:
            return

        # если по этому источнику уже набрали нужное число СТАТЕЙ — прекращаем ходить по нему
        if self._source_reached_limit(r.source.id):
            return

        if not url_allowed(item.url, r):
            return

        await asyncio.sleep(r.source.crawl_policy.request_delay_sec)

        res = await fetch_html(
            session=session,
            url=item.url,
            timeout_sec=r.source.crawl_policy.timeout_sec,
            max_response_bytes=r.source.crawl_policy.max_response_bytes,
            accept_only_content_types=r.source.crawl_policy.accept_only_content_types,
        )
        if res is None:
            return

        # Всегда извлекаем ссылки (даже со страниц-списков)
        for link in self._extract_links(res.html_utf8, base=res.final_url):
            nu = normalize_url(link, self.cfg.dedup.drop_query, self.cfg.dedup.drop_fragment)
            rr = match_source(nu, self.rules)
            if rr is None:
                continue
            if not url_allowed(nu, rr):
                continue
            # если по источнику лимит достигнут — не расширяем его граф
            if self._source_reached_limit(rr.source.id):
                continue
            await self._enqueue_if_new(nu, depth=item.depth + 1)

        # Если это НЕ страница статьи — ничего не сохраняем
        if not url_savable(item.url, r):
            return

        if self.cfg.storage.extract_text:
            text = extract_text_from_html(res.html_utf8)
            sha_text = self.storage.sha256(text)
        else:
            text = ""
            # дедуп хотя бы по HTML, без парсинга
            sha_text = self.storage.sha256(res.html_utf8)

        if self.cfg.dedup.enabled:
            async with self._lock:
                if sha_text in self._text_hash_seen:
                    return
                self._text_hash_seen.add(sha_text)

        # сохранить документ и обновить счётчики
        async with self._lock:
            if self._source_reached_limit(r.source.id):
                return
            if self._doc_id >= self._total_target:
                return
            self._doc_id += 1
            doc_id = self._doc_id
            self._saved_per_source[r.source.id] += 1

        self.storage.store(
            doc_id=doc_id,
            source_id=r.source.id,
            url=res.url,
            final_url=res.final_url,
            status=res.status,
            content_type=res.content_type,
            encoding=res.encoding,
            bytes_len=res.bytes_len,
            html_utf8=res.html_utf8,
            text=text,
        )

        if doc_id % 200 == 0:
            log.info("Saved doc_id=%s total=%s per_source=%s", doc_id, self._doc_id, self._saved_per_source)

    @staticmethod
    def _extract_links(html: str, base: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[str] = []
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            if href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            out.append(urljoin(base, href))
        return out


===== src/crawl/fetcher.py =====
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp
from charset_normalizer import from_bytes


log = logging.getLogger("fetcher")


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    content_type: str
    encoding: str
    html_utf8: str
    bytes_len: int


def _detect_encoding(headers: aiohttp.typedefs.LooseHeaders, body: bytes) -> str:
    # 1) из Content-Type: text/html; charset=...
    ct = str(headers.get("Content-Type", ""))
    lower = ct.lower()
    if "charset=" in lower:
        enc = lower.split("charset=", 1)[1].split(";", 1)[0].strip()
        if enc:
            return enc

    # 2) charset-normalizer
    best = from_bytes(body).best()
    if best and best.encoding:
        return best.encoding

    return "utf-8"


async def fetch_html(
    session: aiohttp.ClientSession,
    url: str,
    timeout_sec: int,
    max_response_bytes: int,
    accept_only_content_types: list[str],
) -> Optional[FetchResult]:
    try:
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        async with session.get(url, timeout=timeout, allow_redirects=True) as resp:
            status = resp.status
            final_url = str(resp.url)
            if status in (403, 429):
                log.warning("HTTP %s for %s (final %s)", status, url, final_url)

            ct = resp.headers.get("Content-Type", "")
            content_type = ct.split(";", 1)[0].strip().lower()

            if accept_only_content_types and content_type not in set(accept_only_content_types):
                return None

            # читаем с лимитом размера
            chunks: list[bytes] = []
            size = 0
            async for chunk in resp.content.iter_chunked(32 * 1024):
                chunks.append(chunk)
                size += len(chunk)
                if size > max_response_bytes:
                    return None

            body = b"".join(chunks)
            enc = _detect_encoding(resp.headers, body)

            try:
                html = body.decode(enc, errors="replace")
            except LookupError:
                html = body.decode("utf-8", errors="replace")
                enc = "utf-8"

            # в любом случае приводим к utf-8 на выходе (строка в Python уже unicode)
            return FetchResult(
                url=url,
                final_url=final_url,
                status=status,
                content_type=content_type,
                encoding=enc,
                html_utf8=html,
                bytes_len=len(body),
            )
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return None


===== src/crawl/rules.py =====
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
    save: List[re.Pattern]     # NEW
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
    # если save_regex не задан — сохраняем всё, что разрешено (fallback)
    if not r.save:
        return url_allowed(url, r)
    return any(s.match(url) for s in r.save)


===== src/crawl/storage.py =====
from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class StoredDoc:
    doc_id: int
    raw_path: str
    text_path: str
    meta_path: str
    sha256_text: str
    text_len: int
    fetch_ts: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Storage:
    def __init__(self, raw_html_dir: str, text_dir: str, meta_dir: str, manifest_path: str, extract_text: bool):
        self.raw_html_dir = raw_html_dir
        self.text_dir = text_dir
        self.meta_dir = meta_dir
        self.manifest_path = manifest_path
        self.extract_text = extract_text

        os.makedirs(self.raw_html_dir, exist_ok=True)
        os.makedirs(self.text_dir, exist_ok=True)
        os.makedirs(self.meta_dir, exist_ok=True)

        if not os.path.exists(self.manifest_path):
            os.makedirs(os.path.dirname(self.manifest_path) or ".", exist_ok=True)
            with open(self.manifest_path, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow([
                    "doc_id", "source_id", "url", "final_url", "fetch_ts",
                    "status", "content_type", "encoding", "bytes_len",
                    "raw_path", "text_path", "meta_path",
                    "sha256_text", "text_len",
                ])

    @staticmethod
    def sha256(s: str) -> str:
        h = hashlib.sha256()
        h.update(s.encode("utf-8", errors="ignore"))
        return h.hexdigest()

    def store(
        self,
        doc_id: int,
        source_id: str,
        url: str,
        final_url: str,
        status: int,
        content_type: str,
        encoding: str,
        bytes_len: int,
        html_utf8: str,
        text: str,
    ) -> StoredDoc:
        fetch_ts = _utc_now_iso()

        raw_path = os.path.join(self.raw_html_dir, f"{doc_id}.html")
        text_path = os.path.join(self.text_dir, f"{doc_id}.txt")
        meta_path = os.path.join(self.meta_dir, f"{doc_id}.json")

        # сохраняем raw html всегда
        with open(raw_path, "w", encoding="utf-8", newline="") as f:
            f.write(html_utf8)

        # сохраняем extracted text только если включено
        if self.extract_text:
            with open(text_path, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            text_len = len(text)
        else:
            text_path = ""  # пустая строка = "файла нет" (удобно для manifest/meta) [web:401]
            text_len = 0

        sha_text = self.sha256(text)
        meta = {
            "doc_id": doc_id,
            "source_id": source_id,
            "url": url,
            "final_url": final_url,
            "fetch_ts": fetch_ts,
            "status": status,
            "content_type": content_type,
            "encoding_detected": encoding,
            "bytes_len": bytes_len,
            "raw_path": raw_path,
            "text_path": text_path,
            "sha256_text": sha_text,
            "text_len": text_len,
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        with open(self.manifest_path, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                doc_id, source_id, url, final_url, fetch_ts,
                status, content_type, encoding, bytes_len,
                raw_path, text_path, meta_path,
                sha_text, text_len,
            ])

        return StoredDoc(
            doc_id=doc_id,
            raw_path=raw_path,
            text_path=text_path,
            meta_path=meta_path,
            sha256_text=sha_text,
            text_len=len(text),
            fetch_ts=fetch_ts,
        )


===== src/crawl/text_extract.py =====
from __future__ import annotations

from bs4 import BeautifulSoup


def extract_text_from_html(html_utf8: str) -> str:
    soup = BeautifulSoup(html_utf8, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    # чуть нормализуем пробелы
    return " ".join(text.split())


===== src/crawl/urlnorm.py =====
from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str, drop_query: bool, drop_fragment: bool) -> str:
    parts = urlsplit(url)
    query = "" if drop_query else parts.query
    fragment = "" if drop_fragment else parts.fragment
    # Не трогаем path: некоторые сайты различают /a и /a/
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, query, fragment))


===== src/robot/config.py =====
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import yaml


@dataclass(frozen=True)
class DBConfig:
    uri: str
    database: str
    documents_collection: str
    frontier_collection: str


@dataclass(frozen=True)
class LogicConfig:
    concurrency: int
    request_delay_sec: float
    revisit_after_sec: int
    lease_sec: int
    error_backoff_sec: int
    reset_stuck_after_sec: int
    max_depth: int
    run_forever: bool


@dataclass(frozen=True)
class RobotConfig:
    db: DBConfig
    logic: LogicConfig
    crawl_config_path: str


def _must(d: Dict[str, Any], key: str) -> Any:
    if key not in d:
        raise ValueError(f"Missing config key: {key}")
    return d[key]


def load_robot_config(path: str) -> RobotConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    db = _must(raw, "db")
    logic = _must(raw, "logic")

    return RobotConfig(
        db=DBConfig(
            uri=str(_must(db, "uri")),
            database=str(_must(db, "database")),
            documents_collection=str(_must(db, "documents_collection")),
            frontier_collection=str(_must(db, "frontier_collection")),
        ),
        logic=LogicConfig(
            concurrency=int(_must(logic, "concurrency")),
            request_delay_sec=float(_must(logic, "request_delay_sec")),
            revisit_after_sec=int(_must(logic, "revisit_after_sec")),
            lease_sec=int(_must(logic, "lease_sec")),
            error_backoff_sec=int(_must(logic, "error_backoff_sec")),
            reset_stuck_after_sec=int(_must(logic, "reset_stuck_after_sec")),
            max_depth=int(_must(logic, "max_depth")),
            run_forever=bool(_must(logic, "run_forever")),
        ),
        crawl_config_path=str(_must(raw, "crawl_config_path")),
    )

===== src/robot/frontier.py =====
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, ReturnDocument


@dataclass(frozen=True)
class FrontierItem:
    url_norm: str
    url: str
    source_id: str
    depth: int


class MongoFrontier:
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str):
        self.col = db[collection_name]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("url_norm", ASCENDING)], unique=True)
        await self.col.create_index([("status", ASCENDING), ("next_fetch_at", ASCENDING)])
        await self.col.create_index([("lease_until", ASCENDING)])

    async def seed(self, *, url_norm: str, url: str, source_id: str, depth: int, now: int) -> None:
        await self.col.update_one(
            {"url_norm": url_norm},
            {
                "$setOnInsert": {
                    "url_norm": url_norm,
                    "url": url,
                    "source_id": source_id,
                    "depth": int(depth),
                    "status": "pending",
                    "next_fetch_at": int(now),
                    "added_at": int(now),
                }
            },
            upsert=True,
        )

    async def enqueue_discovered(self, *, url_norm: str, url: str, source_id: str, depth: int, now: int) -> None:
        # не перетираем существующее (resume/recrawl не ломаем)
        await self.seed(url_norm=url_norm, url=url, source_id=source_id, depth=depth, now=now)

    async def reset_stuck(self, *, now: int, reset_stuck_after_sec: int) -> int:
        # если воркер умер — вернём задачу в pending
        lease_deadline = now - int(reset_stuck_after_sec)
        res = await self.col.update_many(
            {"status": "in_progress", "started_at": {"$lte": lease_deadline}},
            {"$set": {"status": "pending"}, "$unset": {"lease_until": "", "started_at": ""}},
        )
        return int(res.modified_count)

    async def lease_next(self, *, now: int, lease_sec: int) -> Optional[FrontierItem]:
        doc = await self.col.find_one_and_update(
            {"status": "pending", "next_fetch_at": {"$lte": int(now)}},
            {"$set": {"status": "in_progress", "started_at": int(now), "lease_until": int(now + lease_sec)}},
            sort=[("next_fetch_at", ASCENDING), ("added_at", ASCENDING)],
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            return None
        return FrontierItem(
            url_norm=str(doc["url_norm"]),
            url=str(doc["url"]),
            source_id=str(doc["source_id"]),
            depth=int(doc.get("depth", 0)),
        )

    async def finish(self, *, url_norm: str, now: int, next_fetch_at: Optional[int], error: Optional[str] = None) -> None:
        upd = {
            "$set": {
                "updated_at": int(now),
            },
            "$unset": {"lease_until": "", "started_at": ""},
        }
        if error:
            upd["$set"]["last_error"] = str(error)
        else:
            upd["$unset"]["last_error"] = ""

        if next_fetch_at is None:
            upd["$set"]["status"] = "done"
        else:
            upd["$set"]["status"] = "pending"
            upd["$set"]["next_fetch_at"] = int(next_fetch_at)

        await self.col.update_one({"url_norm": url_norm}, upd)

===== src/robot/mongo_storage.py =====
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional
from src.crawl.text_extract import extract_text_from_html
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING


def sha256_hex(s: str) -> str:
    h = hashlib.sha256()
    h.update(s.encode("utf-8", errors="ignore"))
    return h.hexdigest()


@dataclass(frozen=True)
class UpsertResult:
    changed: bool
    existed: bool


class MongoStorage:
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str):
        self.col = db[collection_name]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("url_norm", ASCENDING)], unique=True)
        await self.col.create_index([("checked_at", ASCENDING)])
        await self.col.create_index([("source_id", ASCENDING)])

    async def get_by_url_norm(self, url_norm: str) -> Optional[dict]:
        return await self.col.find_one({"url_norm": url_norm}, {"_id": 0})

    async def upsert_document(
        self,
        *,
        url_norm: str,
        url: str,
        source_id: str,
        source_name: str,
        raw_html: str,
        fetched_status: int,
        content_type: str,
        encoding: str,
        bytes_len: int,
        checked_at: int,
    ) -> UpsertResult:
        text = extract_text_from_html(raw_html)
        new_hash = sha256_hex(text)

        prev = await self.col.find_one({"url_norm": url_norm}, {"_id": 0, "content_hash": 1})
        existed = prev is not None
        prev_hash = (prev or {}).get("content_hash")

        changed = (not existed) or (prev_hash != new_hash)

        update = {
            "$set": {
                "url_norm": url_norm,
                "url": url,
                "source_id": source_id,
                "source_name": source_name,
                "checked_at": checked_at,
                "status": int(fetched_status),
                "content_type": content_type,
                "encoding": encoding,
                "bytes_len": int(bytes_len),
            },
            "$setOnInsert": {
                "first_seen_at": checked_at,
            },
        }

        if changed:
            update["$set"].update(
                {
                    #"raw_html": raw_html,
                    "content_hash": new_hash,
                    "crawled_at": checked_at,
                }
            )

        await self.col.update_one({"url_norm": url_norm}, update, upsert=True)
        return UpsertResult(changed=changed, existed=existed)

===== src/robot/robot.py =====
from __future__ import annotations

import asyncio
import logging
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from motor.motor_asyncio import AsyncIOMotorClient

from src.crawl.config import load_config
from src.crawl.fetcher import fetch_html
from src.crawl.rules import compile_rules, match_source, url_allowed, url_savable
from src.crawl.urlnorm import normalize_url

from .config import RobotConfig
from .frontier import MongoFrontier
from .mongo_storage import MongoStorage

log = logging.getLogger("robot")


class Robot:
    def __init__(self, cfg: RobotConfig):
        self.cfg = cfg

        self.crawl_cfg = load_config(cfg.crawl_config_path)
        self.rules = compile_rules(self.crawl_cfg.sources)

        self.client = AsyncIOMotorClient(cfg.db.uri)
        self.db = self.client[cfg.db.database]

        self.storage = MongoStorage(self.db, cfg.db.documents_collection)
        self.frontier = MongoFrontier(self.db, cfg.db.frontier_collection)

        # --- stats (progress) ---
        self._checked = 0   # сколько URL успешно скачали/обработали (вкл. не-сохраняемые страницы)
        self._updated = 0   # сколько документов реально изменились/вставились
        self._lock_stats = asyncio.Lock()

    async def init(self) -> None:
        await self.storage.ensure_indexes()
        await self.frontier.ensure_indexes()

    async def seed(self) -> None:
        """
        Seed'им frontier только разрешёнными стартовыми URL (start_urls),
        чтобы frontier соответствовал правилам allow/deny.
        """
        now = int(time.time())

        for s in self.crawl_cfg.sources:
            for u in s.start_urls:
                nu = normalize_url(u, self.crawl_cfg.dedup.drop_query, self.crawl_cfg.dedup.drop_fragment)

                r = match_source(nu, self.rules)
                if r is None:
                    continue
                if not url_allowed(nu, r):
                    continue

                await self.frontier.seed(url_norm=nu, url=u, source_id=s.id, depth=0, now=now)

    async def run(self) -> None:
        await self.init()

        reset_count = await self.frontier.reset_stuck(
            now=int(time.time()),
            reset_stuck_after_sec=self.cfg.logic.reset_stuck_after_sec,
        )
        if reset_count:
            log.info("Reset stuck frontier items: %s", reset_count)

        await self.seed()

        workers = [asyncio.create_task(self._worker(i)) for i in range(self.cfg.logic.concurrency)]
        await asyncio.gather(*workers)

    async def _worker(self, wid: int) -> None:
        ua = self.crawl_cfg.sources[0].crawl_policy.user_agent
        timeout_sec = max(s.crawl_policy.timeout_sec for s in self.crawl_cfg.sources)
        max_resp = max(s.crawl_policy.max_response_bytes for s in self.crawl_cfg.sources)

        import aiohttp
        conn = aiohttp.TCPConnector(limit=self.cfg.logic.concurrency)

        async with aiohttp.ClientSession(headers={"User-Agent": ua}, connector=conn) as session:
            idle_rounds = 0

            while True:
                now = int(time.time())
                item = await self.frontier.lease_next(now=now, lease_sec=self.cfg.logic.lease_sec)

                if item is None:
                    if not self.cfg.logic.run_forever:
                        idle_rounds += 1
                        if idle_rounds >= 5:
                            return
                    await asyncio.sleep(1.0)
                    continue

                idle_rounds = 0

                try:
                    await asyncio.sleep(self.cfg.logic.request_delay_sec)

                    r = match_source(item.url_norm, self.rules)
                    if r is None or not url_allowed(item.url_norm, r):
                        await self.frontier.finish(url_norm=item.url_norm, now=now, next_fetch_at=None)
                        continue

                    if item.depth > min(self.cfg.logic.max_depth, r.source.crawl_policy.max_depth):
                        await self.frontier.finish(url_norm=item.url_norm, now=now, next_fetch_at=None)
                        continue

                    res = await fetch_html(
                        session=session,
                        url=item.url,
                        timeout_sec=timeout_sec,
                        max_response_bytes=max_resp,
                        accept_only_content_types=r.source.crawl_policy.accept_only_content_types,
                    )
                    if res is None:
                        await self.frontier.finish(
                            url_norm=item.url_norm,
                            now=now,
                            next_fetch_at=now + self.cfg.logic.error_backoff_sec,
                            error="fetch_failed",
                        )
                        continue

                    # Успешно скачали страницу => считаем "checked"
                    checked_at = int(time.time())
                    async with self._lock_stats:
                        self._checked += 1
                        if self._checked % 500 == 0:
                            log.info("Progress: checked=%s updated=%s", self._checked, self._updated)

                    # 1) discovery: вытаскиваем ссылки (frontier расширяем allow/deny)
                    for link in self._extract_links(res.html_utf8, base=res.final_url):
                        nu = normalize_url(link, self.crawl_cfg.dedup.drop_query, self.crawl_cfg.dedup.drop_fragment)
                        rr = match_source(nu, self.rules)
                        if rr is None:
                            continue
                        if not url_allowed(nu, rr):
                            continue

                        await self.frontier.enqueue_discovered(
                            url_norm=nu,
                            url=link,
                            source_id=rr.source.id,
                            depth=item.depth + 1,
                            now=checked_at,
                        )

                    # 2) store: сохраняем только "корпусные" документы (save_regex)
                    if url_savable(item.url_norm, r):
                        up = await self.storage.upsert_document(
                            url_norm=item.url_norm,
                            url=res.final_url,
                            source_id=r.source.id,
                            source_name=r.source.name,
                            raw_html=res.html_utf8,
                            fetched_status=res.status,
                            content_type=res.content_type,
                            encoding=res.encoding,
                            bytes_len=res.bytes_len,
                            checked_at=checked_at,
                        )

                        if up.changed:
                            log.debug("UPDATED %s (%s)", item.url_norm, r.source.id)

                        async with self._lock_stats:
                            if up.changed:
                                self._updated += 1

                        await self.frontier.finish(
                            url_norm=item.url_norm,
                            now=checked_at,
                            next_fetch_at=checked_at + self.cfg.logic.revisit_after_sec,
                        )
                    else:
                        # Навигационные/листинговые страницы: в documents не кладём,
                        # и не переобкачиваем (одного прохода достаточно, чтобы раскрыть граф ссылок).
                        await self.frontier.finish(url_norm=item.url_norm, now=checked_at, next_fetch_at=None)

                except Exception as e:
                    now2 = int(time.time())
                    await self.frontier.finish(
                        url_norm=item.url_norm,
                        now=now2,
                        next_fetch_at=now2 + self.cfg.logic.error_backoff_sec,
                        error=repr(e),
                    )

    @staticmethod
    def _extract_links(html: str, base: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[str] = []
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            if href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            out.append(urljoin(base, href))
        return out
