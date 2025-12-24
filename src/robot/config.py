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
