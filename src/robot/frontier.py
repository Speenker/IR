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
       
        await self.seed(url_norm=url_norm, url=url, source_id=source_id, depth=depth, now=now)

    async def reset_stuck(self, *, now: int, reset_stuck_after_sec: int) -> int:
       
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
