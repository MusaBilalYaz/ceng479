#!/usr/bin/env python3
"""
process_results.py — Turn raw JMH CSV output into speedup, efficiency and
throughput tables/graphs.

Usage:
    python scripts/process_results.py jmh-results.csv

Expected JMH parameters:
    Param: imageCase   examples: 512x512, 1024x1024, 2048x2048, 3840x2160
    Param: threads     examples: 1, 2, 4, 8, 16
    Param: filterName  examples: Grayscale, GaussianBlur5x5, Sobel3x3

Backward compatibility:
    If the CSV contains Param: size instead of Param: imageCase, the script
    treats it as a square image: size x size.

Outputs:
    speedup_table.csv
    speedup_<FilterName>.png
    efficiency_<FilterName>.png
    speedup_combined_4k_executor.png
    efficiency_combined_4k_executor.png
"""

import csv
import os
import sys
from collections import defaultdict


def load_rows(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def col(row, *candidates):
    """Find a column by trying several possible header spellings."""
    for c in candidates:
        for key in row:
            if key.strip().strip('"').lower() == c.lower():
                value = row[key]
                if value is None:
                    return None
                return value.strip().strip('"')
    return None


def short_method(benchmark):
    """
    Example:
    com.ceng479.imaging.benchmark.FilterBenchmark.executorParallel
    -> executorParallel
    """
    return benchmark.split(".")[-1]


def parse_image_case(value):
    """
    Converts '3840x2160' into ('3840x2160', 3840, 2160).
    Also accepts uppercase X and whitespace.
    """
    if value is None:
        raise ValueError("imageCase is missing")

    normalized = value.lower().replace(" ", "")
    parts = normalized.split("x")

    if len(parts) != 2:
        raise ValueError(f"Invalid imageCase: {value}")

    width = int(parts[0])
    height = int(parts[1])
    label = f"{width}x{height}"
    return label, width, height


def image_area(image_label):
    width, height = map(int, image_label.split("x"))
    return width * height


def image_sort_key(image_label):
    width, height = map(int, image_label.split("x"))
    return (width * height, width, height)


def safe_round(value, digits):
    if value is None:
        return ""
    return round(value, digits)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]
    benchmark_dir = os.path.join("outputs", "benchmark")
    speedup_dir = os.path.join("outputs", "speedup")
    efficiency_dir = os.path.join("outputs", "efficiency")

    os.makedirs(benchmark_dir, exist_ok=True)
    os.makedirs(speedup_dir, exist_ok=True)
    os.makedirs(efficiency_dir, exist_ok=True)
    rows = load_rows(path)

    if not rows:
        print("No rows found in", path)
        sys.exit(1)

    # data[(image_label, filterName)][method][threads] = score_ms
    data = defaultdict(lambda: defaultdict(dict))

    for r in rows:
        bench = col(r, "Benchmark")
        score = col(r, "Score")
        threads = col(r, "Param: threads", "threads")
        fname = col(r, "Param: filterName", "filterName")

        # Preferred proposal-aligned parameter.
        image_case_value = col(r, "Param: imageCase", "imageCase")

        # Backward compatibility for older benchmark code.
        size_value = col(r, "Param: size", "size")

        if bench is None or score is None or threads is None or fname is None:
            continue

        method = short_method(bench)

        try:
            score_ms = float(score.replace(",", "."))
            threads_i = int(threads)

            if image_case_value:
                image_label, width, height = parse_image_case(image_case_value)
            elif size_value:
                size_i = int(size_value)
                width = size_i
                height = size_i
                image_label = f"{width}x{height}"
            else:
                continue

        except (TypeError, ValueError):
            continue

        data[(image_label, fname)][method][threads_i] = score_ms

    if not data:
        print("No usable benchmark rows found. Check CSV parameter names.")
        sys.exit(1)

    # ---------------------------------------------------------------------
    # Build speedup / efficiency / throughput table
    # ---------------------------------------------------------------------

    header = [
        "image",
        "filter",
        "threads",
        "sequential_ms",
        "executor_ms",
        "forkjoin_ms",
        "executor_speedup",
        "forkjoin_speedup",
        "executor_efficiency",
        "forkjoin_efficiency",
        "executor_throughput_mpixels_per_sec",
        "forkjoin_throughput_mpixels_per_sec",
    ]

    out_rows = []

    print("\n" + " ".join(f"{h:>22}" for h in header))
    print("-" * (24 * len(header)))

    for (image_label, fname) in sorted(data.keys(), key=lambda k: (image_sort_key(k[0]), str(k[1]))):
        methods = data[(image_label, fname)]

        seq_scores = methods.get("sequential", {})
        if not seq_scores:
            continue

        # Sequential ignores the thread parameter; prefer threads=1 if present.
        seq_ms = seq_scores.get(1, next(iter(seq_scores.values())))

        all_threads = sorted(
            set(methods.get("executorParallel", {}).keys())
            | set(methods.get("forkJoinParallel", {}).keys())
        )

        pixels = image_area(image_label)
        megapixels = pixels / 1_000_000.0

        for threads in all_threads:
            exec_ms = methods.get("executorParallel", {}).get(threads)
            fj_ms = methods.get("forkJoinParallel", {}).get(threads)

            exec_sp = (seq_ms / exec_ms) if exec_ms else None
            fj_sp = (seq_ms / fj_ms) if fj_ms else None

            exec_eff = (exec_sp / threads) if exec_sp else None
            fj_eff = (fj_sp / threads) if fj_sp else None

            exec_tp = (megapixels / (exec_ms / 1000.0)) if exec_ms else None
            fj_tp = (megapixels / (fj_ms / 1000.0)) if fj_ms else None

            row = [
                image_label,
                fname,
                threads,
                safe_round(seq_ms, 3),
                safe_round(exec_ms, 3),
                safe_round(fj_ms, 3),
                safe_round(exec_sp, 2),
                safe_round(fj_sp, 2),
                safe_round(exec_eff, 2),
                safe_round(fj_eff, 2),
                safe_round(exec_tp, 2),
                safe_round(fj_tp, 2),
            ]

            out_rows.append(row)
            print(" ".join(f"{str(v):>22}" for v in row))

    speedup_table_path = os.path.join(benchmark_dir, "speedup_table.csv")

    with open(speedup_table_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(out_rows)

    print(f"\nWrote {speedup_table_path}")

    # ---------------------------------------------------------------------
    # Optional charts
    # ---------------------------------------------------------------------

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        filters = sorted({fname for (_, fname) in data.keys()})
        images = sorted({image for (image, _) in data.keys()}, key=image_sort_key)
        largest_image = images[-1]

        # Per-filter speedup charts: ExecutorService vs ForkJoinPool
        for fname in filters:
            fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
            fig.suptitle(f"Speedup vs Threads — {fname}", fontsize=13)

            for ax, (method_key, method_label) in zip(
                axes,
                [
                    ("executorParallel", "ExecutorService"),
                    ("forkJoinParallel", "ForkJoinPool"),
                ],
            ):
                for image_label in images:
                    methods = data.get((image_label, fname), {})
                    seq_scores = methods.get("sequential", {})

                    if not seq_scores:
                        continue

                    seq_ms = seq_scores.get(1, next(iter(seq_scores.values())))
                    threads_sorted = sorted(methods.get(method_key, {}).keys())

                    if not threads_sorted:
                        continue

                    speedups = [seq_ms / methods[method_key][t] for t in threads_sorted]
                    ax.plot(threads_sorted, speedups, marker="o", label=image_label)

                ax.plot([1, 16], [1, 16], "k--", alpha=0.35, label="ideal")
                ax.set_title(method_label)
                ax.set_xlabel("Thread count")
                ax.set_ylabel("Speedup (T_seq / T_parallel)")
                ax.legend(fontsize=8)
                ax.grid(True, alpha=0.3)

            plt.tight_layout()
            out = os.path.join(speedup_dir, f"speedup_{fname}.png")
            plt.savefig(out, dpi=120, bbox_inches="tight")
            plt.close()
            print("Wrote", out)

        # Per-filter efficiency charts: ExecutorService vs ForkJoinPool
        for fname in filters:
            fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
            fig.suptitle(f"Efficiency vs Threads — {fname}", fontsize=13)

            for ax, (method_key, method_label) in zip(
                axes,
                [
                    ("executorParallel", "ExecutorService"),
                    ("forkJoinParallel", "ForkJoinPool"),
                ],
            ):
                for image_label in images:
                    methods = data.get((image_label, fname), {})
                    seq_scores = methods.get("sequential", {})

                    if not seq_scores:
                        continue

                    seq_ms = seq_scores.get(1, next(iter(seq_scores.values())))
                    threads_sorted = sorted(methods.get(method_key, {}).keys())

                    if not threads_sorted:
                        continue

                    efficiencies = [
                        (seq_ms / methods[method_key][t]) / t for t in threads_sorted
                    ]
                    ax.plot(threads_sorted, efficiencies, marker="o", label=image_label)

                ax.axhline(1.0, color="k", linestyle="--", alpha=0.35, label="ideal")
                ax.set_title(method_label)
                ax.set_xlabel("Thread count")
                ax.set_ylabel("Efficiency (Speedup / Threads)")
                ax.legend(fontsize=8)
                ax.grid(True, alpha=0.3)

            plt.tight_layout()
            out = os.path.join(efficiency_dir, f"efficiency_{fname}.png")
            plt.savefig(out, dpi=120, bbox_inches="tight")
            plt.close()
            print("Wrote", out)

        # Combined speedup chart: all filters on the largest image, ExecutorService
        plt.figure(figsize=(8, 5))
        filter_colors = {
            "GaussianBlur5x5": "tab:red",
            "Sobel3x3": "tab:blue",
            "Grayscale": "tab:green",
        }

        for fname in filters:
            methods = data.get((largest_image, fname), {})
            seq_scores = methods.get("sequential", {})

            if not seq_scores:
                continue

            seq_ms = seq_scores.get(1, next(iter(seq_scores.values())))
            threads_sorted = sorted(methods.get("executorParallel", {}).keys())

            if not threads_sorted:
                continue

            speedups = [seq_ms / methods["executorParallel"][t] for t in threads_sorted]
            plt.plot(
                threads_sorted,
                speedups,
                marker="o",
                color=filter_colors.get(fname, None),
                label=fname,
            )

        plt.plot([1, 16], [1, 16], "k--", alpha=0.35, label="ideal (linear)")
        plt.title(f"Speedup vs Threads — All Filters ({largest_image}, Executor)")
        plt.xlabel("Thread count")
        plt.ylabel("Speedup (T_seq / T_parallel)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        out = os.path.join(speedup_dir, "speedup_combined_4k_executor.png")
        plt.savefig(out, dpi=120, bbox_inches="tight")
        plt.close()
        print("Wrote", out)

        # Combined efficiency chart: all filters on the largest image, ExecutorService
        plt.figure(figsize=(8, 5))

        for fname in filters:
            methods = data.get((largest_image, fname), {})
            seq_scores = methods.get("sequential", {})

            if not seq_scores:
                continue

            seq_ms = seq_scores.get(1, next(iter(seq_scores.values())))
            threads_sorted = sorted(methods.get("executorParallel", {}).keys())

            if not threads_sorted:
                continue

            efficiencies = [
                (seq_ms / methods["executorParallel"][t]) / t for t in threads_sorted
            ]
            plt.plot(
                threads_sorted,
                efficiencies,
                marker="o",
                color=filter_colors.get(fname, None),
                label=fname,
            )

        plt.axhline(1.0, color="k", linestyle="--", alpha=0.35, label="ideal")
        plt.title(f"Efficiency vs Threads — All Filters ({largest_image}, Executor)")
        plt.xlabel("Thread count")
        plt.ylabel("Efficiency (Speedup / Threads)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        out = os.path.join(efficiency_dir, "efficiency_combined_4k_executor.png")
        plt.savefig(out, dpi=120, bbox_inches="tight")
        plt.close()
        print("Wrote", out)

    except ImportError:
        print("\nmatplotlib is not installed — skipping charts.")
        print("Install with: pip install matplotlib")


if __name__ == "__main__":
    main()