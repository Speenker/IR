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

        
        self._checked = 0  
        self._updated = 0  
        self._lock_stats = asyncio.Lock()

    async def init(self) -> None:
        await self.storage.ensure_indexes()
        await self.frontier.ensure_indexes()

    async def seed(self) -> None:
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

                   
                    checked_at = int(time.time())
                    async with self._lock_stats:
                        self._checked += 1
                        if self._checked % 500 == 0:
                            log.info("Progress: checked=%s updated=%s", self._checked, self._updated)

                   
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
