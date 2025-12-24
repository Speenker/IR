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
   
    ct = str(headers.get("Content-Type", ""))
    lower = ct.lower()
    if "charset=" in lower:
        enc = lower.split("charset=", 1)[1].split(";", 1)[0].strip()
        if enc:
            return enc

   
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
