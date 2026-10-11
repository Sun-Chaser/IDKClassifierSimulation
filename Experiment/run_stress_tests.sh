#!/usr/bin/env bash
# Activate your Conda environment before launching this script.
# Usage: bash Experiment/run_stress_tests.sh [--dry-run] [m_equal m_random n_equal k_equal]
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname -- "$SCRIPT_DIR")"

# Settings may be overridden with environment variables when launching.
PYTHON="${PYTHON:-python}"
TRIALS="${TRIALS:-100}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-60}"
MAX_STATES="${MAX_STATES:-2000000}"
LOG_FILE="${LOG_FILE:-$PROJECT_DIR/log.txt}"
# Edit this list to choose what runs when no experiment names are supplied.
DEFAULT_EXPERIMENTS=(m_equal m_random)

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    shift
fi
EXPERIMENTS=("${DEFAULT_EXPERIMENTS[@]}")
if (( $# > 0 )); then
    EXPERIMENTS=("$@")
fi
# Validate the full selection before starting any experiments.
for experiment in "${EXPERIMENTS[@]}"; do
    case "$experiment" in
        m_equal|m_random|n_equal|k_equal) ;;
        *) printf 'Unknown experiment: %s\nChoose: m_equal m_random n_equal k_equal\n' "$experiment" >&2; exit 2 ;;
    esac
done

# Append so restarting a batch preserves earlier logs. Python output is unbuffered.
exec >> "$LOG_FILE" 2>&1
export PYTHONUNBUFFERED=1
trap 'status=$?; printf "[%s] Batch finished (exit=%s)\n" "$(date -u +%FT%TZ)" "$status"' EXIT
printf '\n[%s] Starting batch; trials=%s; experiments=%s; dry_run=%s\n' \
    "$(date -u +%FT%TZ)" "$TRIALS" "${EXPERIMENTS[*]}" "$DRY_RUN"
"$PYTHON" -c 'import sys; print("Python:", sys.executable, sys.version, flush=True)'

run_command() {
    printf 'Command:'
    printf ' %q' "$@"
    printf '\n'
    if [[ "$DRY_RUN" == false ]]; then
        "$@"
    fi
}

for experiment in "${EXPERIMENTS[@]}"; do
    # Bounds are inclusive. Keep every range as START END [STEP].
    case "$experiment" in
        m_equal) parameters=(--m 2 8 --n 5 5 --k 1 1 --row-sizes equal) ;;
        m_random) parameters=(--m 2 8 --n 5 5 --k 1 1 --row-sizes random) ;;
        n_equal) parameters=(--m 4 4 --n 5 30 5 --k 2 2 --row-sizes equal) ;;
        k_equal) parameters=(--m 4 4 --n 20 20 --k 1 19 3 --include-all --row-sizes equal) ;;
    esac
    # Separate config per batch; repeated launches never replace an earlier config.
    config="$SCRIPT_DIR/Config/${experiment}_${TRIALS}_$(date -u +%Y%m%dT%H%M%SZ)_$$.json"
    printf '[%s] Starting %s\n' "$(date -u +%FT%TZ)" "$experiment"
    run_command "$PYTHON" "$SCRIPT_DIR/generate_config.py" \
        "${parameters[@]}" --trials "$TRIALS" --max-states "$MAX_STATES" \
        --timeout-seconds "$TIMEOUT_SECONDS" --output "$config"
    run_command "$PYTHON" "$SCRIPT_DIR/run_experiments.py" --config "$config"
    printf '[%s] Finished %s\n' "$(date -u +%FT%TZ)" "$experiment"
done
