#!/usr/bin/env bash
set -euo pipefail

# ---------- Edit these settings before each run ----------
EXPERIMENT_NAME="my_experiment"   # A filename-friendly name of your choice
M=(2 8 1)                       # Start, end (inclusive), step
N=(5 5 1)                       # Same start/end means one value
K=(1 1 1)                       # Use K=(all) for unrestricted search
TRIALS=100                      # Seeds: 42, 43, ..., 42 + TRIALS - 1
ROW_SIZES="equal"               # "equal" or "random"
TIMEOUT_SECONDS=60              # Maximum time for each trial
MAX_STATES=2000000              # Skip cases above this state count
PYTHON="python"                 # Uses your activated Conda environment
# ---------------------------------------------------------

# Find the project, even when launched from a different working directory.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname -- "$SCRIPT_DIR")"

# Clear log.txt and send all experiment output and errors there.
exec > "$PROJECT_DIR/log.txt" 2>&1
export PYTHONUNBUFFERED=1
trap 'status=$?; echo "Finished at $(date); exit code: $status"' EXIT

# Give each run its own config and results so previous results are preserved.
RUN_NAME="${EXPERIMENT_NAME}_$(date -u +%Y%m%dT%H%M%SZ)_$$"
CONFIG_FILE="$SCRIPT_DIR/Config/$RUN_NAME.json"
RESULT_DIR="$SCRIPT_DIR/results/$RUN_NAME"

echo "Starting experiment: $EXPERIMENT_NAME"
echo "Started at: $(date)"
echo "Config: $CONFIG_FILE"
echo "Results: $RESULT_DIR"

# 1. Generate the config from the settings above.
"$PYTHON" "$SCRIPT_DIR/generate_config.py" \
    --m "${M[@]}" --n "${N[@]}" --k "${K[@]}" \
    --trials "$TRIALS" --row-sizes "$ROW_SIZES" \
    --timeout-seconds "$TIMEOUT_SECONDS" --max-states "$MAX_STATES" \
    --output "$CONFIG_FILE"

# 2. Run this experiment only (all parameter combinations in its config).
"$PYTHON" "$SCRIPT_DIR/run_experiments.py" \
    --config "$CONFIG_FILE" --output "$RESULT_DIR"
