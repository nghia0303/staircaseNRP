#!/usr/bin/env bash
# Compare four AllSAT enumeration backends on the same Ladder amongNurse CNF.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
source "$repo_root/scripts/linux_env.sh"

if [[ $# -eq 0 ]]; then
    classes=(2)
    horizons=(40)
elif [[ $# -eq 1 && $1 == --grid ]]; then
    classes=(1 2 3)
    horizons=(40 50 60 70 80)
elif [[ $# -eq 2 ]]; then
    classes=("$1")
    horizons=("$2")
else
    echo "Usage: bash experiments/src/runner/run_among_nurse_ladder_solvers.sh [CLASS HORIZON | --grid]" >&2
    exit 2
fi

all_methods=(g421-legacy-enum-models g421-projected cadical195-projected tabularallsat)
if [[ -n "${LADDER_SOLVER_METHODS:-}" ]]; then
    read -r -a methods <<< "$LADDER_SOLVER_METHODS"
else
    methods=("${all_methods[@]}")
fi
if ((${#methods[@]} == 0)); then
    echo "LADDER_SOLVER_METHODS is empty" >&2
    exit 2
fi

for class_id in "${classes[@]}"; do
    if [[ ! "$class_id" =~ ^[123]$ ]]; then
        echo "CLASS must be 1, 2, or 3: $class_id" >&2
        exit 2
    fi
done
for horizon in "${horizons[@]}"; do
    case "$horizon" in
        40|50|60|70|80) ;;
        *) echo "HORIZON must be 40, 50, 60, 70, or 80: $horizon" >&2; exit 2 ;;
    esac
done
declare -A seen_methods=()
for method in "${methods[@]}"; do
    if [[ ! " ${all_methods[*]} " == *" $method "* ]]; then
        echo "Unknown method: $method" >&2
        exit 2
    fi
    if [[ -n "${seen_methods[$method]:-}" ]]; then
        echo "Duplicate method: $method" >&2
        exit 2
    fi
    seen_methods[$method]=1
done

python_bin="${LADDER_SOLVER_PYTHON_BIN:-$NRP_VENV/bin/python}"
driver="$repo_root/experiments/src/methods/among_nurse_ladder_solvers.py"
solver_source="${TABULAR_ALLSAT_SOURCE:-$NRP_NATIVE_HOME/src/tabularAllSAT}"
solver_bin="${TABULAR_ALLSAT_BIN:-$solver_source/cdcl-vsads/solver}"
timeout_s="${LADDER_SOLVER_TIMEOUT_S:-300}"
output_root="${LADDER_SOLVER_OUTPUT_ROOT:-$repo_root/experiments/runs/amongNurse-ladder-solvers}"

if [[ -n "${LADDER_SOLVER_MEMORY_MB:-}" ]]; then
    memory_mb="$LADDER_SOLVER_MEMORY_MB"
else
    total_memory_mb="$(awk '/^MemTotal:/ {printf "%d\n", $2 / 1024; exit}' /proc/meminfo)"
    memory_mb="$((total_memory_mb - 6144))"
    if ((memory_mb < 1024)); then memory_mb=1024; fi
fi

if [[ ! -x "$python_bin" ]]; then
    echo "Missing Python: $python_bin" >&2
    exit 2
fi
if [[ ! -f "$driver" ]]; then
    echo "Missing driver: $driver" >&2
    exit 2
fi
if ! command -v runlim >/dev/null || [[ ! -x /usr/bin/time ]]; then
    echo "runlim and /usr/bin/time are required" >&2
    exit 2
fi
if [[ ! "$timeout_s" =~ ^[1-9][0-9]*$ || ! "$memory_mb" =~ ^[1-9][0-9]*$ ]]; then
    echo "LADDER_SOLVER_TIMEOUT_S and LADDER_SOLVER_MEMORY_MB must be positive integers" >&2
    exit 2
fi
if [[ " ${methods[*]} " == *" tabularallsat "* ]]; then
    if [[ ! -x "$solver_bin" ]]; then
        echo "Missing TabularAllSAT: $solver_bin (see docs/TABULAR_ALLSAT.md)" >&2
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
fi

mkdir -p "$output_root"
run_dir="$(mktemp -d "$output_root/$(date +%Y%m%d_%H%M%S)_XXXXXX")"
total_runs=$((${#classes[@]} * ${#horizons[@]} * ${#methods[@]}))
run_number=0
failed=0

echo "Output dir: $run_dir"
echo "Plan: C=[${classes[*]}], H=[${horizons[*]}], methods=[${methods[*]}], runs=$total_runs"
echo "Per-run limits: ${timeout_s}s; ${memory_mb} MB RAM"
echo "Elapsed metric: GNU wall time for the complete method process; runlim overhead is excluded."

for class_id in "${classes[@]}"; do
    for horizon in "${horizons[@]}"; do
        for method in "${methods[@]}"; do
            run_number=$((run_number + 1))
            safe_method="${method//-/_}"
            prefix="$run_dir/ladder_${safe_method}_C${class_id}_H${horizon}"
            stdout_file="$prefix.stdout.txt"
            runlim_file="$prefix.runlim.txt"
            gnu_time_file="$prefix.gnu_time.txt"
            exit_file="$prefix.exit_code.txt"
            report="$prefix.json"
            args=(
                --method "$method"
                --class-id "$class_id"
                --horizon "$horizon"
                --output-dir "$run_dir"
                --timeout-s "$timeout_s"
            )
            if [[ "$method" == tabularallsat ]]; then
                args+=(--solver-bin "$solver_bin")
            fi
            if [[ "${LADDER_SOLVER_VALIDATE_MODELS:-0}" == 1 ]]; then
                args+=(--validate-models)
            fi

            printf '[%d/%d] C=%s H=%s | %s: START\n' \
                "$run_number" "$total_runs" "$class_id" "$horizon" "$method"

            if runlim -o "$runlim_file" -r "$((timeout_s + 60))" -s "$memory_mb" \
                    bash -c '
                        exit_file=$1
                        gnu_time_file=$2
                        shift 2
                        /usr/bin/time -f "%e" -o "$gnu_time_file" "$@"
                        code=$?
                        printf "%s\n" "$code" > "$exit_file"
                        exit "$code"
                    ' _ "$exit_file" "$gnu_time_file" \
                    timeout --foreground --signal=TERM --kill-after=5s "${timeout_s}s" \
                    "$python_bin" -B "$driver" "${args[@]}" \
                    > "$stdout_file" 2>&1; then
                run_code=0
            else
                run_code=$?
            fi

            child_code=125
            if [[ -s "$exit_file" ]]; then child_code="$(<"$exit_file")"; fi
            if ((run_code != 0)) || [[ "$child_code" != 0 ]] || [[ ! -s "$report" ]]; then
                failed=$((failed + 1))
                echo "    ERROR/TIMEOUT | child=$child_code runlim=$run_code | log: $stdout_file"
                continue
            fi

            "$python_bin" -B - "$report" "$gnu_time_file" <<'PY'
import json
from pathlib import Path
import sys

report = json.loads(Path(sys.argv[1]).read_text())
elapsed = Path(sys.argv[2]).read_text().strip().splitlines()[-1]
print(f"    {report['status'].upper()} | solutions: {report['reported_solutions']:,} | "
      f"elapsed: {float(elapsed):.3f}s | solver: {report['solver']}")
PY
        done
    done
done

if ! "$python_bin" -B - "$run_dir" <<'PY'
import csv
import json
from pathlib import Path
import re
import sys

run_dir = Path(sys.argv[1])
columns = (
    "method", "class_id", "horizon", "status", "reported_solutions",
    "solver", "enumeration_mode", "n_vars", "n_clauses_initial",
    "encoding_wall_s", "cnf_write_wall_s", "solver_wall_s",
    "total_internal_wall_s", "gnu_time_real_s", "runlim_cpu_s",
    "runlim_space_mb", "projected_blocking_clauses",
    "full_model_blocking_clauses", "validation", "report",
)
rows = []
for report_path in sorted(run_dir.glob("*.json")):
    data = json.loads(report_path.read_text())
    row = {key: data.get(key) for key in columns}
    row["report"] = str(report_path)
    stem = report_path.with_suffix("")
    gnu_file = Path(str(stem) + ".gnu_time.txt")
    if gnu_file.is_file():
        matches = re.findall(r"^([0-9]+(?:\.[0-9]+)?)\s*$", gnu_file.read_text(), re.M)
        if matches:
            row["gnu_time_real_s"] = float(matches[-1])
    runlim_file = Path(str(stem) + ".runlim.txt")
    if runlim_file.is_file():
        content = runlim_file.read_text(errors="replace")
        for field, label in (("runlim_cpu_s", "time"), ("runlim_space_mb", "space")):
            match = re.search(r"^\[runlim\] " + label + r":\s*([0-9.]+)", content, re.M)
            if match:
                row[field] = float(match.group(1))
    rows.append(row)

groups = {}
for row in rows:
    if row["status"] == "complete":
        groups.setdefault((row["class_id"], row["horizon"]), set()).add(row["reported_solutions"])
mismatches = {key: counts for key, counts in groups.items() if len(counts) > 1}
if mismatches:
    for (class_id, horizon), counts in sorted(mismatches.items()):
        print(f"Count mismatch for C={class_id}, H={horizon}: {sorted(counts)}", file=sys.stderr)
    for row in rows:
        if (row["class_id"], row["horizon"]) in mismatches and row["status"] == "complete":
            row["status"] = "count_mismatch"

with (run_dir / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

raise SystemExit(1 if mismatches else 0)
PY
then
    failed=$((failed + 1))
fi

echo "Completed: $((total_runs - failed))/$total_runs. Summary: $run_dir/summary.csv"
if ((failed > 0)); then
    exit 1
fi
