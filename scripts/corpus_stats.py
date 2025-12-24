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

    print("Documents:", stats["documents_total"])
    print("Per source:", stats["per_source"])
    print("RAW sum MB:", round(stats["raw_html"]["sum_bytes"] / (1024 * 1024), 2))
    print("RAW avg KB:", round(stats["raw_html"]["avg_bytes"] / 1024, 2))
    print("TEXT sum MB:", round(stats["text"]["sum_bytes"] / (1024 * 1024), 2))
    print("TEXT avg KB:", round(stats["text"]["avg_bytes"] / 1024, 2))
    print("Wrote:", str(OUT_JSON))


if __name__ == "__main__":
    main()
