import argparse
import csv
import random
from pathlib import Path


def read_termfreq(path: Path) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        header = next(r, None)  
        for row in r:
            if not row or len(row) < 2:
                continue
            term = (row[0] or "").strip()
            if not term:
                continue
            try:
                freq = int(row[1])
            except ValueError:
                continue
            if freq > 0:
                rows.append((term, freq))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Top terms + anti-top (rare) from term_freq.csv")
    ap.add_argument("--termfreq", default="out/term_freq.csv", help="Path to term_freq.csv")
    ap.add_argument("--top", type=int, default=20, help="Top-N terms by collection frequency")
    ap.add_argument("--hapax", type=int, default=20, help="How many freq=1 example terms to print")
    ap.add_argument("--seed", type=int, default=42, help="Random seed for sampling freq=1 examples")
    args = ap.parse_args()

    termfreq_path = Path(args.termfreq)
    if not termfreq_path.exists():
        raise SystemExit(f"Not found: {termfreq_path}")

    rows = read_termfreq(termfreq_path)
    if not rows:
        raise SystemExit(f"No data in: {termfreq_path}")

    total_terms = len(rows)
    total_tokens = sum(freq for _, freq in rows)

    rows_sorted = sorted(rows, key=lambda x: (-x[1], x[0]))
    topn = rows_sorted[: max(1, args.top)]

    print("== TOP terms (by collection frequency) ==")
    print(f"Total unique terms: {total_terms}")
    print(f"Total tokens (sum freq): {total_tokens}")
    print("rank,term,freq,share_%")
    for i, (term, freq) in enumerate(topn, 1):
        share = (100.0 * freq / total_tokens) if total_tokens else 0.0
        print(f"{i},{term},{freq},{share:.6f}")

    freq1 = [t for t, f in rows if f == 1]
    freq2 = [t for t, f in rows if f == 2]
    freq3_5 = [t for t, f in rows if 3 <= f <= 5]

    def pct(x: int) -> float:
        return (100.0 * x / total_terms) if total_terms else 0.0

    print("\n== Anti-top (rare terms) ==")
    print(f"freq=1 terms: {len(freq1)} ({pct(len(freq1)):.2f}%)")
    print(f"freq=2 terms: {len(freq2)} ({pct(len(freq2)):.2f}%)")
    print(f"freq=3..5 terms: {len(freq3_5)} ({pct(len(freq3_5)):.2f}%)")

    random.seed(args.seed)
    examples = freq1
    if len(examples) > args.hapax:
        examples = random.sample(examples, args.hapax)

    print(f"\nExamples of freq=1 terms (n={len(examples)}):")
    for t in sorted(examples):
        print(t)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
