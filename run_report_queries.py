import re
import subprocess
import sys
from pathlib import Path

EXE = sys.argv[1] if len(sys.argv) > 1 else "search_cli.exe"
INV = sys.argv[2] if len(sys.argv) > 2 else r"index\inv.bin"
FWD = sys.argv[3] if len(sys.argv) > 3 else r"index\fwd.bin"
LIMIT = int(sys.argv[4]) if len(sys.argv) > 4 else 3

QUERIES = [
    ("AND", "дорога && ремонт"),
    ("OR", "полиция || суд"),
    ("NOT", "город && !москва"),
    ("Скобки", "(полиция || суд) && (дело || приговор)"),
    ("TF IDF", "проект развитие"),
]

def clean_title(s: str, max_len: int = 80) -> str:
    s = s.replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()

    for cut in [" Температура", " НУ И ПОГОДА", " Меню Новости", " Новости "]:
        if cut in s and s.lower().startswith("новости"):
            s = s.split(cut, 1)[0].strip()

    if "»" in s:
        s = s.split("»", 1)[0].strip()
    s = re.sub(r"\s*Ковровские вести.*$", "", s).strip()

    s = re.sub(r"\s*Размер шрифта:.*$", "", s).strip()
    s = re.sub(r"\s*Межбуквенный интервал:.*$", "", s).strip()

    s = re.sub(r"\s*Мы используем cookie.*$", "", s).strip()

    if len(s) > max_len:
        s = s[: max_len - 3].rstrip() + "..."
    return s

def run_one_query(q: str) -> str:
    qfile = Path("one_query.txt")
    qfile.write_text(q + "\n", encoding="utf-8")

    cmd = [EXE, "--inv", INV, "--fwd", FWD, "--queries", str(qfile), "--limit", str(LIMIT)]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(p.stdout + "\n" + p.stderr)
    return p.stdout

def parse_lines(out: str):
    rows = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < 3:
            continue

        if len(parts) == 3 and re.fullmatch(r"\d+", parts[0]):
            docid = parts[0]
            title = clean_title(parts[1])
            url = parts[2]
            rows.append(("B", docid, "", title, url))
            continue

        if len(parts) >= 4 and re.fullmatch(r"\d+", parts[0]) and re.fullmatch(r"\d+\.\d+", parts[1]):
            docid = parts[0]
            score = parts[1]
            title = clean_title(parts[2])
            url = parts[3]
            rows.append(("T", docid, score, title, url))
            continue

    return rows

def print_block(kind: str, label: str, query: str, rows):
    print("Тип запроса\t" + label)
    print("Запрос\t" + query)

    if kind == "TFIDF":
        print("docid\tscore\ttitle\turl")
        for _, docid, score, title, url in rows:
            print(f"{docid}\t{score}\t{title}\t{url}")
    else:
        print("docid\ttitle\turl")
        for _, docid, _, title, url in rows:
            print(f"{docid}\t{title}\t{url}")

    print()

def main():
    for label, q in QUERIES:
        out = run_one_query(q)
        rows = parse_lines(out)
        kind = "TFIDF" if label == "TF IDF" else "BOOL"
        print_block(kind, label, q, rows)

if __name__ == "__main__":
    main()
