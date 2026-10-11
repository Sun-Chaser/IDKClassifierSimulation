"""Run reproducible DP parameter sweeps in isolated, time-limited processes."""
import argparse
import csv
from datetime import datetime, timezone
import itertools
import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from DPSimulation import DPSimulation
from RandomClassifierSetGenerator import RandomSetGenerator


def validate(config):
    for key in ("m", "n", "k", "seeds"):
        values = config.get(key)
        if not isinstance(values, list) or not values:
            raise ValueError(f"{key} must be a nonempty array")
        for value in values:
            if key == "k" and value == "all":
                continue
            if type(value) is not int or (key != "seeds" and value < 1):
                raise ValueError(f"Invalid {key} value: {value!r}")
    if config.get("row_sizes") not in ("equal", "random"):
        raise ValueError('row_sizes must be "equal" or "random"')
    timeout = config.get("timeout_seconds")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout_seconds must be finite and positive")
    if type(config.get("max_states")) is not int or config["max_states"] < 1:
        raise ValueError("max_states must be a positive integer")


def inputs(case):
    return RandomSetGenerator(
        case["m"], case["n"], seed=case["seed"],
        equal_row_length=case["row_sizes"],
    ).generate_sets()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def worker(case):
    result = dict(case)
    result["status"] = "error"
    try:
        p, c = inputs(case)
        lengths = [len(row) - 1 for row in p[1:]]
        count = math.prod(length + 1 for length in lengths)
        result.update(row_lengths=lengths, predicted_states=count)
        if count > case["max_states"]:
            result["status"] = "skipped_state_limit"
        else:
            sim = DPSimulation(p, c)
            start = time.perf_counter()
            try:
                value = sim.run("all") if case["k"] == "all" else sim.run("k", K=case["k"])
            finally:
                result["solve_seconds"] = time.perf_counter() - start
                result["states_visited"] = len(sim.V)
            start = time.perf_counter()
            state = (0,) * case["m"]
            path = []
            while sim.choice[state] is not None:
                i, j = sim.choice[state]
                path.append({"set": i, "classifier": j})
                state = state[:i - 1] + (j,) + state[i:]
            result.update(status="ok", expected_cost=value, path=path,
                          path_length=len(path), trace_seconds=time.perf_counter() - start)
    except RecursionError as exc:
        result.update(status="recursion_error", error=str(exc))
    except MemoryError:
        result.update(status="memory_error", error="Worker ran out of memory")
    except Exception as exc:
        result.update(status="error", error=f"{type(exc).__name__}: {exc}")
    return result


def run(config, output):
    validate(config)
    output.mkdir(parents=True, exist_ok=False)
    save(output / "config.json", config)
    save(output / "environment.json", {
        "python": sys.version, "platform": sys.platform,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "recursion_limit": sys.getrecursionlimit(),
    })
    fields = ["seed", "compute_time_seconds", "expected_cost", "path_length", "number_of_states"]
    # Duplicate parameter values must not overwrite an earlier experiment.
    combinations = itertools.product(*(dict.fromkeys(config[key]) for key in ("m", "n", "k")))
    for m, n, k in combinations:
        filename = (f"m{m}_n{n}_k{k}_ms{config['max_states']}_"
                    f"{config['row_sizes']}_{len(config['seeds'])}.csv")
        with (output / filename).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for trial, seed in enumerate(config["seeds"], 1):
                case = dict(m=m, n=n, k=k, seed=seed, row_sizes=config["row_sizes"],
                            max_states=config["max_states"])
                try:
                    completed = subprocess.run(
                        [sys.executable, str(Path(__file__).resolve()), "--worker"],
                        input=json.dumps(case), capture_output=True, text=True,
                        timeout=config["timeout_seconds"],
                    )
                    if completed.returncode != 0:
                        result = dict(status="worker_error", error=completed.stderr[-4000:])
                    else:
                        result = json.loads(completed.stdout)
                except subprocess.TimeoutExpired:
                    result = dict(status="timeout")
                writer.writerow(dict(
                    seed=seed, compute_time_seconds=result.get("solve_seconds"),
                    expected_cost=result.get("expected_cost"),
                    path_length=result.get("path_length"),
                    number_of_states=result.get("states_visited"),
                ))
                stream.flush()
                if result["status"] != "ok":
                    with (output / "failures.log").open("a") as log:
                        log.write(f"{filename} trial={trial} seed={seed}: "
                                  f"{result['status']} {result.get('error', '')}\n")
                print(f"m={m} n={n} k={k} seed={seed}: {result['status']}", flush=True)
    print(f"Results: {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--output", type=Path, help="New directory for this sweep")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(json.load(sys.stdin)), allow_nan=False))
        return
    config = json.loads(args.config.read_text())
    output = args.output or Path(__file__).with_name("results") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    try:
        run(config, output.resolve())
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
