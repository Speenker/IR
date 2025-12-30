import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
TERM_FREQ_CSV = BASE_DIR / "out" / "term_freq.csv"
OUT_PNG = BASE_DIR / "out" / "zipf_plot.png"


def read_freqs(path: Path):
    freqs = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        next(r, None) 
        for row in r:
            if len(row) < 2:
                continue
            try:
                freq = int(row[1])
            except ValueError:
                continue
            if freq > 0:
                freqs.append(freq)
    freqs.sort(reverse=True)
    return np.array(freqs, dtype=np.float64)


def subsample_log(ranks, freqs, points=2000):
    n = len(ranks)
    if n <= points:
        return ranks, freqs
   
    idx = np.unique(
        np.logspace(0, np.log10(n), num=points, dtype=int) - 1
    )
    return ranks[idx], freqs[idx]


def main():
    if not TERM_FREQ_CSV.exists():
        raise SystemExit(f"Not found: {TERM_FREQ_CSV}")

    freqs = read_freqs(TERM_FREQ_CSV)
    if freqs.size == 0:
        raise SystemExit("No frequencies found")

    ranks = np.arange(1, freqs.size + 1, dtype=np.float64)
    f1 = freqs[0]
    zipf_pred = f1 / ranks

   
    ranks_s, freqs_s = subsample_log(ranks, freqs, points=2000)
    _, zipf_s = subsample_log(ranks, zipf_pred, points=2000)

    plt.figure(figsize=(8, 6))

   
    plt.loglog(ranks_s, freqs_s, color="blue", linewidth=1.5, label="Корпус")

   
    plt.loglog(ranks_s, zipf_s, color="red", linewidth=1.5, label="Zipf: f1/r")

    plt.xlabel("Ранг термина (log r)")
    plt.ylabel("Частота (log f)")
    plt.title("Закон Ципфа для корпуса")
    plt.legend()
    plt.grid(True, which="both", linestyle="--", alpha=0.3)

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150)
    print(f"Saved plot to {OUT_PNG}")


if __name__ == "__main__":
    main()
