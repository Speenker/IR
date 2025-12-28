import argparse
import csv
import os
import re
import statistics
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


DEFAULT_QUERIES = [
    
    "серпухов",
    "области",
    "новости",
    
    "серпухов AND области",
    "серпухов OR области",
    "NOT серпухов",
    
    "премии AND губернатора AND подмосковье",
    "ремонт OR дорога",
    "культура AND музей",
]


@dataclass
class RunResult:
    query: str
    mode: str  
    ok: bool
    elapsed_ms: float
    hits: int
    score_min: Optional[float]
    score_med: Optional[float]
    score_max: Optional[float]
    stderr: str


SCORE_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def parse_cli_output(stdout_text: str) -> tuple[int, list[float], str]:
    """
    Returns: (hits, scores, mode)
    mode = "ranked" if a score column exists, else "boolean"
    """
    hits = 0
    scores: list[float] = []
    mode = "boolean"

    for line in stdout_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        
        if len(parts) >= 4 and SCORE_RE.match(parts[1]):
            mode = "ranked"
            hits += 1
            try:
                scores.append(float(parts[1]))
            except ValueError:
                pass
        elif len(parts) >= 3 and parts[0].isdigit():
            hits += 1

    return hits, scores, mode


def one_run(cli: str, inv: str, fwd: str, query: str, limit: int, offset: int) -> RunResult:
    t0 = time.perf_counter()
    p = subprocess.run(
        [cli, "--inv", inv, "--fwd", fwd, "--offset", str(offset), "--limit", str(limit)],
        input=(query + "\n").encode("utf-8", errors="ignore"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    t1 = time.perf_counter()

    stdout = p.stdout.decode("utf-8", errors="ignore")
    stderr = p.stderr.decode("utf-8", errors="ignore").strip()

    hits, scores, mode = parse_cli_output(stdout)
    ok = (p.returncode == 0)

    if scores:
        score_min = min(scores)
        score_med = statistics.median(scores)
        score_max = max(scores)
    else:
        score_min = score_med = score_max = None

    return RunResult(
        query=query,
        mode=mode,
        ok=ok,
        elapsed_ms=(t1 - t0) * 1000.0,
        hits=hits,
        score_min=score_min,
        score_med=score_med,
        score_max=score_max,
        stderr=stderr,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Benchmark searchcli response time and basic output stats")
    ap.add_argument("--cli", default="./search_cli.exe", help="Path to searchcli(.exe)")
    ap.add_argument("--inv", default="./index/inv.bin", help="Path to inv.bin")
    ap.add_argument("--fwd", default="./index/fwd.bin", help="Path to fwd.bin")
    ap.add_argument("--queries", default="", help="Path to text file with queries (one per line)")
    ap.add_argument("--repeat", type=int, default=10, help="How many runs per query")
    ap.add_argument("--limit", type=int, default=50, help="--limit for searchcli")
    ap.add_argument("--offset", type=int, default=0, help="--offset for searchcli")
    ap.add_argument("--warmup", type=int, default=1, help="Warmup runs per query (not recorded)")
    ap.add_argument("--out-runs", default="out/search_bench_runs.csv", help="CSV with all runs")
    ap.add_argument("--out-summary", default="out/search_bench_summary.csv", help="CSV summary per query")
    args = ap.parse_args()

    cli = args.cli
    if not os.path.exists(cli) and os.path.exists(cli.replace("./", "./") + ".exe"):
        cli = cli + ".exe"

    for p in [cli, args.inv, args.fwd]:
        if not os.path.exists(p):
            raise SystemExit(f"Not found: {p}")

    if args.queries:
        qpath = Path(args.queries)
        queries = [ln.strip() for ln in qpath.read_text(encoding="utf-8", errors="ignore").splitlines()]
        queries = [q for q in queries if q and not q.startswith("#")]
    else:
        queries = DEFAULT_QUERIES

    Path(args.out_runs).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_summary).parent.mkdir(parents=True, exist_ok=True)

    all_runs: list[RunResult] = []

    for q in queries:
        for _ in range(max(0, args.warmup)):
            _ = one_run(cli, args.inv, args.fwd, q, args.limit, args.offset)

    for q in queries:
        for _ in range(max(1, args.repeat)):
            all_runs.append(one_run(cli, args.inv, args.fwd, q, args.limit, args.offset))

    with open(args.out_runs, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query", "mode", "ok", "elapsed_ms", "hits", "score_min", "score_med", "score_max", "stderr"])
        for r in all_runs:
            w.writerow([
                r.query, r.mode, int(r.ok), f"{r.elapsed_ms:.3f}", r.hits,
                "" if r.score_min is None else f"{r.score_min:.6f}",
                "" if r.score_med is None else f"{r.score_med:.6f}",
                "" if r.score_max is None else f"{r.score_max:.6f}",
                r.stderr[:200].replace("\n", " "),
            ])

    byq: dict[str, list[RunResult]] = {}
    for r in all_runs:
        byq.setdefault(r.query, []).append(r)

    with open(args.out_summary, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "query", "mode",
            "runs", "ok_runs", "hits_med",
            "latency_ms_min", "latency_ms_med", "latency_ms_p95", "latency_ms_max",
            "score_med_min", "score_med_med", "score_med_max",
        ])
        for q, rr in byq.items():
            rr_sorted = sorted(rr, key=lambda x: x.elapsed_ms)
            lat = [x.elapsed_ms for x in rr_sorted]
            hits = [x.hits for x in rr_sorted]
            mode = max((x.mode for x in rr), key=lambda m: sum(1 for x in rr if x.mode == m))
            ok_runs = sum(1 for x in rr if x.ok)

            p95 = lat[int(0.95 * (len(lat) - 1))] if len(lat) > 1 else lat[0]

            score_meds = [x.score_med for x in rr if x.score_med is not None]
            if score_meds:
                score_med_min = min(score_meds)
                score_med_med = statistics.median(score_meds)
                score_med_max = max(score_meds)
            else:
                score_med_min = score_med_med = score_med_max = None

            w.writerow([
                q, mode,
                len(rr), ok_runs, int(statistics.median(hits)),
                f"{min(lat):.3f}", f"{statistics.median(lat):.3f}", f"{p95:.3f}", f"{max(lat):.3f}",
                "" if score_med_min is None else f"{score_med_min:.6f}",
                "" if score_med_med is None else f"{score_med_med:.6f}",
                "" if score_med_max is None else f"{score_med_max:.6f}",
            ])

    print(f"Wrote: {args.out_runs}")
    print(f"Wrote: {args.out_summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
