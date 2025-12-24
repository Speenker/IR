import csv
import os
from pathlib import Path

from bs4 import BeautifulSoup


RAW_DIR = Path("data/raw_html")
TEXT_DIR = Path("data/text")
MANIFEST = Path("data/manifest.csv")


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    
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
