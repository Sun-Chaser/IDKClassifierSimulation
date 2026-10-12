# Experiment plots

All plotting code, dependencies, and generated output live in `Plot/`.
From the repository root, install the dependency once:

```sh
python -m pip install -r requirements.txt
```

Run with prompts to choose the experiment results folder, x, and y:

```sh
python Plot/plot_experiments.py
```

Or supply the choices directly:

```sh
python Plot/plot_experiments.py --experiment Experiment/results/20261011T224450_652246Z --x n --y runtime
python Plot/plot_experiments.py --experiment Experiment/results/20261011T224450_652246Z --x n --y expected_cost
```

- `--x`: `n`, `m`, or `k`.
- `--y`: `runtime` (solve time in seconds) or `expected_cost`.
- `--groupby`: one or more parameters separating lines, e.g. `--groupby n` or `--groupby n k`. Must differ from x.
- `--show`: also open a plot window.

Each point is the trial mean, with error bars of ±1 **sample standard
deviation** (`ddof=1`). A single valid trial has a mean but no SD error bar.
Incomplete trials or nonfinite measurements are excluded from both metrics;
a completed trial must contain finite runtime and expected cost. The script
prints the omitted count. Empty combinations have blank mean/SD in the summary.

For example, plot runtime against m with one line per n:

```sh
python Plot/plot_experiments.py --experiment Experiment/results/YOUR_EXPERIMENT --x m --y runtime --groupby n
```

Use `--groupby k` for one line per k, or `--groupby n k` for one line
per (n, k) pair. Each point pools all valid trial rows sharing its x value
and selected group values, including any varying parameters not selected.
Its standard deviation is calculated over these pooled trial rows. For example,
`--groupby n` pools k values if k varies; choose `--groupby n k` to keep them
separate. The summary CSV contains x, the group parameters, count, mean, and std.

Without `--groupby`, separate lines keep all other parameters, row size mode,
and state limit fixed, preserving the original behavior. Interactive x selection
also prompts for grouping; press Enter for the default.
Numeric x values are sorted numerically. If k includes `all`, all x positions
are categorical, with `all` last. The script reads the current per-combination
CSV format directly inside the selected folder; it does not combine experiment
folders or support older result formats.

Each run saves a PNG, PDF, and summary CSV (parameters, count, mean, std) in
`Plot/output/<experiment-folder>/<timestamp>/`. Source experiment files are
read only. Run again after an ongoing experiment completes to include its latest
trials.
