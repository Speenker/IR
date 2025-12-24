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
                    "content_hash": new_hash,
                    "crawled_at": checked_at,
                }
            )

        await self.col.update_one({"url_norm": url_norm}, update, upsert=True)
        return UpsertResult(changed=changed, existed=existed)
