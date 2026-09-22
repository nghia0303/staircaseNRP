#!/usr/bin/env bash
# Only the projected TabularAllSAT rerun for legacy amongNurse.
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/scripts/linux_env.sh"

if [[ $# -eq 0 ]]; then
    classes=(3)
    horizons=(40)
elif [[ $# -eq 1 && $1 == --grid ]]; then
    classes=(1 2 3)
    horizons=(40 50 60 70 80)
elif [[ $# -eq 2 ]]; then
    classes=("$1")
    horizons=("$2")
else
    echo "Usage: bash run_all_sat.sh [CLASS HORIZON | --grid]" >&2
    exit 2
fi

python_bin="${ALLSAT_PYTHON_BIN:-$NRP_VENV/bin/python}"
solver_source="${TABULAR_ALLSAT_SOURCE:-$NRP_NATIVE_HOME/src/tabularAllSAT}"
solver_bin="${TABULAR_ALLSAT_BIN:-$solver_source/cdcl-vsads/solver}"
timeout_s="${ALLSAT_TIMEOUT_S:-300}"
memory_mb="${ALLSAT_MEMORY_MB:-4096}"
output_root="${ALLSAT_OUTPUT_ROOT:-$SRC_PATH/tmp/amongNurse-allsat}"
run_dir="$output_root/$(date +%Y%m%d_%H%M%S)_$$"

if [[ ! -x "$python_bin" ]]; then
    echo "Missing Python: $python_bin (set NRP_VENV or ALLSAT_PYTHON_BIN)" >&2
    exit 2
fi
if [[ ! -x "$solver_bin" ]]; then
    echo "Missing TabularAllSAT: $solver_bin (see docs/TABULAR_ALLSAT.md)" >&2
    exit 2
fi
if [[ ! "$timeout_s" =~ ^[1-9][0-9]*$ || ! "$memory_mb" =~ ^[1-9][0-9]*$ ]]; then
    echo "ALLSAT_TIMEOUT_S and ALLSAT_MEMORY_MB must be positive integers" >&2
    exit 2
fi
if [[ -z "${TABULAR_ALLSAT_BIN:-}" ]]; then
    expected=ad4a071310581990b7834f1f076ccfb54d592bbf
    actual="$(git -C "$solver_source" rev-parse HEAD)"
    if [[ "$actual" != "$expected" ]]; then
        echo "Wrong TabularAllSAT commit: $actual (expected $expected)" >&2
        exit 2
    fi
fi

mkdir -p "$run_dir"
echo "AllSAT outputs: $run_dir"
failed=0
for class_id in "${classes[@]}"; do
    for horizon in "${horizons[@]}"; do
        for method in ladder de; do
            args=(
                --method "$method" --class-id "$class_id" --horizon "$horizon"
                --solver-bin "$solver_bin" --output-dir "$run_dir"
                --timeout-s "$timeout_s"
            )
            if [[ "${ALLSAT_VALIDATE_MODELS:-0}" == 1 ]]; then args+=(--validate-models); fi
            echo "Running $method, C-${class_id}, H=${horizon}"
            report="$run_dir/${method}_C${class_id}_H${horizon}.json"
            if runlim -r "$((timeout_s + 60))" -s "$memory_mb" \
                    "$python_bin" -B "$SRC_PATH/src/test/NRP_2010_allsat.py" "${args[@]}" \
                    2> "$run_dir/${method}_C${class_id}_H${horizon}.runlim.txt" \
                    | tee "$run_dir/${method}_C${class_id}_H${horizon}.stdout.txt"; then
                pipeline_ok=1
            else
                pipeline_ok=0
            fi
            if ((pipeline_ok == 0)) || [[ ! -s "$report" ]] || ! grep -q '"status": "complete"' "$report"; then
                failed=$((failed + 1))
                echo "Incomplete run: $method C-${class_id} H=${horizon}; see $run_dir" >&2
            fi
        done
    done
done
if ((failed > 0)); then
    echo "$failed AllSAT run(s) incomplete; other runs were kept in $run_dir" >&2
    exit 1
fi
