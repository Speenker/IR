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

       
        self._doc_id = max_doc_id

       
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
        
        if self._doc_id >= self._total_target:
            return

        r = match_source(item.url, self.rules)
        if r is None:
            return

        if item.depth > r.source.crawl_policy.max_depth:
            return

        
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

        
        for link in self._extract_links(res.html_utf8, base=res.final_url):
            nu = normalize_url(link, self.cfg.dedup.drop_query, self.cfg.dedup.drop_fragment)
            rr = match_source(nu, self.rules)
            if rr is None:
                continue
            if not url_allowed(nu, rr):
                continue
            
            if self._source_reached_limit(rr.source.id):
                continue
            await self._enqueue_if_new(nu, depth=item.depth + 1)

        
        if not url_savable(item.url, r):
            return

        if self.cfg.storage.extract_text:
            text = extract_text_from_html(res.html_utf8)
            sha_text = self.storage.sha256(text)
        else:
            text = ""
            
            sha_text = self.storage.sha256(res.html_utf8)

        if self.cfg.dedup.enabled:
            async with self._lock:
                if sha_text in self._text_hash_seen:
                    return
                self._text_hash_seen.add(sha_text)

        
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
