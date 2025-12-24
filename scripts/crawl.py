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
