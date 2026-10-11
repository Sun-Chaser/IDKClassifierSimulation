# Simulation experiments

From the repository root, run:

```sh
python3 Experiment/run_experiments.py
```

Edit `Experiment/Config/config.json` to set arrays of `m`, `n`, `k`, and `seeds`.
The runner evaluates every combination. Use positive integers for m, n, k;
`"all"` in the k array selects unrestricted search. Integer k >= n is
also equivalent to unrestricted search. Seeds are integers.

```json
{
  "m": [3, 4, 5],
  "n": [5, 10, 20],
  "k": [1, 2, 5, "all"],
  "seeds": [42, 43, 44],
  "row_sizes": "equal",
  "timeout_seconds": 60,
  "max_states": 1000000
}
```

- `row_sizes: "equal"` gives every set exactly n classifiers for controlled scaling.
- `row_sizes: "random"` uses the existing RandomSetGenerator: lengths vary from 1
  to n, with at least one full-length row. The seed and dimensions determine the
  inputs; all k values use identical inputs for a given seed and dimensions.
- `timeout_seconds` limits each fresh worker process, including startup and input
  generation. Timed-out workers are killed and reaped before the next case.
- `max_states` skips solving cases where the product of (row length + 1) exceeds
  the limit. This is a state-count guard, not an enforced memory budget. Input
  generation occurs before this check, so avoid enormous individual dimensions.

Each invocation creates a new UTC-timestamped directory in `Experiment/results/`:

- `config.json`: complete sweep settings.
- `environment.json`: Python version, platform, recursion limit, and start time.
- One CSV per (m, n, k) combination, named
  `m{m}_n{n}_k{k}_ms{max_states}_{row_sizes}_{trial_count}.csv`.
  For example, `m5_n5_k5_ms100000_equal_3.csv` contains three trial rows.
  The trial count is the length of the seeds array; `k="all"` appears as `kall`.
- `failures.log`, only when needed, records failed/skipped trial statuses.

CSV columns contain raw measurements: `seed`, `compute_time_seconds`,
`expected_cost`, `path_length`, and `number_of_states`.
Compute time measures only the DP solve, excluding process startup, input
creation, and path extraction. Number of states is the number actually cached
by the solver, not the predicted state count. Path length counts the selected
classifier attempts along successive failures until termination.
Each seed produces one row, flushed immediately. Failed or skipped trials have
blank unavailable metrics; details are in `failures.log`. The filename trial
count includes these attempted trials. No per-trial JSON files are written.
Configuration and environment JSON snapshots remain sweep-level metadata.
Each case runs sequentially in a fresh process to isolate cache and memory.

The generator also supports this directly:

```python
RandomSetGenerator(5, 10, seed=42, equal_row_length="equal")
```

`equal_row_length` defaults to `"random"`; `"equal"` makes every set contain
exactly N classifiers. The runner passes its existing `row_sizes` setting to
this parameter, preserving the configuration format.

Use separate configurations for the proposed sweeps: increase m with n fixed,
increase n with m fixed, then sweep k on a shared problem. Compare expected cost
as well as solve time when choosing k. Begin with small state counts, increasing
`max_states` deliberately as memory and runtime measurements allow.

Alternative settings and output location:

```sh
python3 Experiment/run_experiments.py --config Experiment/Config/config.json --output Experiment/results/my_sweep
```

The output directory must not already exist, preventing accidental overwrites.
Older result directories retain their original format.

## Generate a configuration

Supply `START END [STEP]` for m, n, and k, using inclusive bounds:
END is included when reached by STEP; STEP defaults to 1.

```sh
python3 Experiment/generate_config.py --m 1 4 --n 5 20 5 --k 1 3 --trials 10
python3 Experiment/run_experiments.py
```

This writes m=[1,2,3,4], n=[5,10,15,20], k=[1,2,3], and seeds 42 through
51 to `Experiment/Config/config.json`, replacing that config if it exists.
Each parameter combination uses the same seed array. For one value, use
the same start and end: `--m 5 5` produces [5]. Negative steps are
supported for descending ranges; empty ranges and zero steps are rejected.

Use `--k all` for unrestricted search only, or `--include-all` to append
unrestricted search to a numeric k range. Other settings remain scalars:
`--trials 10`, `--row-sizes equal` (or `random`), `--timeout-seconds 60`,
`--max-states 1000000`, and `--output Experiment/Config/custom_config.json`.
Seeds always start at 42 and increase by 1.
With no arguments, the generator uses m=[3,4], n=[5,10], k=[1,2], and
seeds=[42,43,44]. Custom output can be run with the runner's `--config` flag.

## Background batches with nohup

Activate the Conda environment first. The script inherits its Python executable.
By default it runs `m_equal` and `m_random`, with 100 trials per configuration
(1,400 trials total, seeds 42–141). It runs experiments sequentially.

```sh
conda activate idk_env
nohup bash Experiment/run_stress_tests.sh > /dev/null 2>&1 < /dev/null &
echo $!  # Batch process ID
 tail -f log.txt
```

The script appends stdout and stderr to the project-root `log.txt`, including
commands, interpreter details, timestamps, per-trial statuses, and result paths.
Configs are stored in `Experiment/Config`; CSV results remain in timestamped
`Experiment/results` directories. A script error stops the batch; individual
trial failures/timeouts are recorded by the runner and do not stop other trials.

Choose experiments by name, or edit `DEFAULT_EXPERIMENTS` in the script:

```sh
nohup bash Experiment/run_stress_tests.sh m_equal n_equal k_equal m_random > /dev/null 2>&1 < /dev/null &
```

- `m_equal`: m=2–8, n=5, k=1, equal row lengths.
- `m_random`: same dimensions, random row lengths.
- `n_equal`: m=4, n=5–30 in steps of 5, k=2.
- `k_equal`: m=4, n=20, k=1–19 in steps of 3, plus unrestricted search.

Preview commands without generating configs or running simulations:

```sh
bash Experiment/run_stress_tests.sh --dry-run m_equal n_equal k_equal m_random
```

The preview also appends to `log.txt`. Override settings at launch if needed:

```sh
TRIALS=200 TIMEOUT_SECONDS=120 MAX_STATES=2000000 nohup bash Experiment/run_stress_tests.sh m_equal > /dev/null 2>&1 < /dev/null &
```

`PYTHON` and `LOG_FILE` can also be overridden. The default timeout is 60 seconds
per trial and the default state limit is 2,000,000; it is not a memory limit.
