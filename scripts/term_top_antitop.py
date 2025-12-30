import argparse
import csv
import random
from pathlib import Path


# Должно совпадать со списком stopwords в build_index/search_cli. [file:13]
STOPWORDS = {
    "и","в","во","не","что","он","на","я","с","со","как","а","то","все","она","так","его","но","да",
    "ты","к","у","же","вы","за","бы","по","ее","мне","было","вот","от","меня","еще","нет","о","из",
    "ему","теперь","когда","даже","ну","вдруг","ли","если","уже","или","ни","быть","был","него","до",
    "вас","нибудь","опять","уж","вам","ведь","там","потом","себя","ничего","ей","может","они","тут",
    "где","есть","надо","ней","для","мы","тебя","их","чем","была","сам","чтоб","без","будто","чего",
    "раз","тоже","себе","под","будет","ж","тогда","кто","этот","того","потому","этого","какой","совсем",
    "ним","здесь","этом","один","почти","мой","тем","чтобы","нее","сейчас","были","куда","зачем","всех",
    "никогда","можно","при","наконец","два","об","другой","хоть","после","над","больше","тот","через",
    "эти","нас","про","всего","них","какая","много","разве","три","эту","моя","впрочем","хорошо","свою",
    "этой","перед","иногда","лучше","чуть","том","нельзя","такой","им","более","всегда","конечно","всю",
    "между",
}


def read_termfreq(path: Path, *, drop_stopwords: bool = True) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        _ = next(r, None)  # header
        for row in r:
            if not row or len(row) < 2:
                continue
            term = (row[0] or "").strip()
            if not term:
                continue

            if drop_stopwords and term in STOPWORDS:
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
    ap.add_argument(
        "--keep-stopwords",
        action="store_true",
        help="Do not filter stopwords (by default stopwords are removed).",
    )
    args = ap.parse_args()

    termfreq_path = Path(args.termfreq)
    if not termfreq_path.exists():
        raise SystemExit(f"Not found: {termfreq_path}")

    rows = read_termfreq(termfreq_path, drop_stopwords=not args.keep_stopwords)
    if not rows:
        raise SystemExit(f"No data in (after filtering): {termfreq_path}")

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
