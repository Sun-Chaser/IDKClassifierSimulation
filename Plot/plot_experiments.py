"""Plot experiment trial means with ±1 sample standard deviation error bars."""
import argparse
import csv
from collections import defaultdict
from datetime import datetime
import math
import os
from pathlib import Path
import re
import statistics

PLOT_DIR = Path(__file__).resolve().parent
CASE = re.compile(r"m(?P<m>\d+)_n(?P<n>\d+)_k(?P<k>\d+|all)_ms(?P<max_states>\d+)_(?P<row_sizes>equal|random)_(?P<trials>\d+)\.csv")
METRICS = {"runtime": ("compute_time_seconds", "Runtime (seconds)"),
           "expected_cost": ("expected_cost", "Expected cost")}


def summarize(folder, x, y, groupby=None):
    """Pool trials by x and selected grouping parameters, excluding invalid trials."""
    groups = defaultdict(list)
    omitted = 0
    matched = 0
    if groupby is not None:
        if not groupby or any(name not in ("m", "n", "k") for name in groupby):
            raise ValueError("groupby must contain one or more of m, n, k")
        if x in groupby:
            raise ValueError("The x axis cannot also be a groupby parameter")
        if len(set(groupby)) != len(groupby):
            raise ValueError("groupby parameters must not be repeated")
    fixed = list(groupby) if groupby is not None else [
        name for name in ("m", "n", "k", "max_states", "row_sizes") if name != x
    ]
    for path in sorted(folder.glob("*.csv")):
        match = CASE.fullmatch(path.name)
        if not match:
            continue
        matched += 1
        params = match.groupdict()
        key = tuple(params[name] for name in fixed)
        coordinate = params[x]
        groups[key, coordinate]  # Retain empty groups in the summary.
        with path.open(newline="") as stream:
            reader = csv.DictReader(stream)
            if not {"compute_time_seconds", "expected_cost"}.issubset(reader.fieldnames or []):
                raise ValueError(f"Missing metric columns in {path}")
            for row in reader:
                try:
                    # Failed solves can record elapsed time without a cost.
                    runtime = float(row["compute_time_seconds"])
                    cost = float(row["expected_cost"])
                    if not math.isfinite(runtime) or not math.isfinite(cost):
                        raise ValueError
                except (ValueError, TypeError):
                    omitted += 1
                    continue
                groups[key, coordinate].append(runtime if y == "runtime" else cost)
    if not matched:
        raise ValueError(f"No supported experiment CSV files found in {folder}")
    rows = []
    for (key, coordinate), values in groups.items():
        rows.append(dict(zip(fixed, key), **{x: coordinate}, count=len(values),
                         mean=statistics.mean(values) if values else None,
                         std=statistics.stdev(values) if len(values) > 1 else None))
    return fixed, rows, omitted


def draw(folder, x, y, fixed, rows, output, show=False):
    os.environ.setdefault("MPLCONFIGDIR", str(PLOT_DIR / ".cache"))
    os.environ.setdefault("XDG_CACHE_HOME", str(PLOT_DIR / ".cache"))
    try:
        import matplotlib
        if not show:
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ValueError("Install plotting dependencies: python -m pip install -r requirements.txt") from exc
    valid = [row for row in rows if row["count"]]
    if not valid:
        raise ValueError("No completed trials with finite measurements to plot")
    series = defaultdict(list)
    for row in valid:
        series[tuple(row[name] for name in fixed)].append(row)
    coordinates = sorted({row[x] for row in rows}, key=lambda v: (v == "all", int(v) if v != "all" else 0))
    # 'all' has no numerical distance; use categorical positions when present.
    positions = {v: i if "all" in coordinates else int(v) for i, v in enumerate(coordinates)}
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for key, points in sorted(series.items()):
        points.sort(key=lambda row: positions[row[x]])
        label = ", ".join(f"{name}={value}" for name, value in zip(fixed, key))
        ax.plot([positions[p[x]] for p in points], [p["mean"] for p in points], "o-", label=label)
        color = ax.lines[-1].get_color()
        with_std = [p for p in points if p["std"] is not None]
        ax.errorbar([positions[p[x]] for p in with_std], [p["mean"] for p in with_std],
                    yerr=[p["std"] for p in with_std], fmt="none", capsize=4, color=color)
    ax.set(xlabel=x, ylabel=METRICS[y][1], title=f"{folder.name}\nMean ± sample standard deviation")
    ax.set_xticks([positions[v] for v in coordinates], coordinates)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize="small")
    fig.tight_layout()
    output.mkdir(parents=True, exist_ok=True)
    stem = f"{y}_vs_{x}"
    fig.savefig(output / f"{stem}.png", dpi=200)
    fig.savefig(output / f"{stem}.pdf")
    with (output / f"{stem}_summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[x, *fixed, "count", "mean", "std"])
        writer.writeheader()
        writer.writerows(rows)
    if show:
        plt.show()
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, help="Experiment results folder containing CSV files")
    parser.add_argument("--x", choices=("n", "m", "k"))
    parser.add_argument("--y", choices=tuple(METRICS))
    parser.add_argument("--groupby", nargs="+", choices=("m", "n", "k"),
                        help="One line per group (e.g. --groupby n k); pool other parameters. Default: keep all other parameters separate")
    parser.add_argument("--show", action="store_true", help="Also open an interactive plot window")
    args = parser.parse_args()
    try:
        folder = args.experiment or Path(input("Experiment results folder: ").strip()).expanduser()
        x = args.x or input("X axis (n/m/k): ").strip().lower()
        y = args.y or input("Y axis (runtime/expected_cost): ").strip().lower().replace(" ", "_")
        folder = folder.expanduser().resolve()
        if not folder.is_dir():
            raise ValueError(f"Experiment folder does not exist: {folder}")
        if x not in ("n", "m", "k") or y not in METRICS:
            raise ValueError("Choose x from n, m, k and y from runtime, expected_cost")
        groupby = args.groupby
        if groupby is None and args.x is None:
            answer = input("Group lines by (m/n/k, space-separated; Enter for automatic): ").strip().lower()
            groupby = answer.split() if answer else None
        fixed, rows, omitted = summarize(folder, x, y, groupby)
        output = PLOT_DIR / "output" / folder.name / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        draw(folder, x, y, fixed, rows, output, args.show)
        print(f"Saved PNG, PDF, and summary CSV to {output}")
        print(f"Omitted {omitted} incomplete or invalid trials. Single-trial points have no SD error bar.")
    except (ValueError, OSError, EOFError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
