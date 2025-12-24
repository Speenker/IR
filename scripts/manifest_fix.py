import csv
import hashlib
from pathlib import Path

MANIFEST_IN  = Path("data/manifest.csv")
MANIFEST_OUT = Path("data/manifest_fixed.csv")

RAW_DIR  = Path("data/raw_html")
TEXT_DIR = Path("data/text")
META_DIR = Path("data/meta")

TEXT_ENCODING = "utf-8" 


def sha256_hex(s: str) -> str:
    h = hashlib.sha256()
    h.update(s.encode("utf-8", errors="ignore"))
    return h.hexdigest()


def main() -> None:
    if not MANIFEST_IN.exists():
        raise SystemExit(f"Input manifest not found: {MANIFEST_IN}")

    with MANIFEST_IN.open("r", encoding="utf-8", newline="") as fin:
        reader = csv.DictReader(fin)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise SystemExit("Manifest has no header")

    
        expected = [
            "doc_id", "source_id", "url", "final_url", "fetch_ts",
            "status", "content_type", "encoding", "bytes_len",
            "raw_path", "text_path", "meta_path",
            "sha256_text", "text_len",
        ]

        for col in expected:
            if col not in fieldnames:
                fieldnames.append(col)

        MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
        with MANIFEST_OUT.open("w", encoding="utf-8", newline="") as fout:
            writer = csv.DictWriter(fout, fieldnames=fieldnames)
            writer.writeheader()

            total = 0
            fixed = 0

            for row in reader:
                total += 1
                doc_id = (row.get("doc_id") or "").strip()
                if not doc_id:
                    writer.writerow(row)
                    continue

                
                rawpath  = RAW_DIR  / f"{doc_id}.html"
                textpath = TEXT_DIR / f"{doc_id}.txt"
                metapath = META_DIR / f"{doc_id}.json"

                
                if rawpath.exists():
                    row["raw_path"] = str(rawpath).replace("/", "\\")
                if textpath.exists():
                    row["text_path"] = str(textpath).replace("/", "\\")
                if metapath.exists():
                    row["meta_path"] = str(metapath).replace("/", "\\")

                
                if rawpath.exists():
                    try:
                        size = rawpath.stat().st_size
                        row["bytes_len"] = str(size)
                    except OSError:
                        pass

                
                if textpath.exists():
                    try:
                        text = textpath.read_text(
                            encoding=TEXT_ENCODING,
                            errors="ignore",
                        )
                    except OSError:
                        text = ""
                    text = text.rstrip("\r\n")
                    if text:
                        row["text_len"] = str(len(text))
                        row["sha256_text"] = sha256_hex(text)
                    else:
                
                        row["text_len"] = row.get("text_len") or "0"
                else:
                    row["text_len"] = row.get("text_len") or "0"

                fixed += 1
                writer.writerow(row)

    print(f"DONE. Processed {total} rows, wrote {fixed} rows to {MANIFEST_OUT}")


if __name__ == "__main__":
    main()
