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

       
        with open(raw_path, "w", encoding="utf-8", newline="") as f:
            f.write(html_utf8)

       
        if self.extract_text:
            with open(text_path, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            text_len = len(text)
        else:
            text_path = "" 
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
