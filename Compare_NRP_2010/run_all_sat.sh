#!/usr/bin/env bash
# Rerun amongNurse with TabularAllSAT, PySAT g421, and the legacy methods.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -z "${NRP_VENV:-}" && -x "$repo_root/.venv/bin/python" ]]; then
    export NRP_VENV="$repo_root/.venv"
fi
source "$repo_root/scripts/linux_env.sh"

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

all_methods=(ladder pblib_bdd-pblib_bdd de
    sat_g421_staircase-binomial sat_g421_pblib_bdd-pblib_bdd sat_g421_pblib_bdd-binomial
    classic amongMDD2 seqMDD2 CPLEX_CP CPLEX_MP Gurobi Picat)
if [[ -n "${ALLSAT_METHODS:-}" ]]; then
    read -r -a methods <<< "$ALLSAT_METHODS"
else
    methods=("${all_methods[@]}")
fi
if ((${#methods[@]} == 0)); then
    echo "ALLSAT_METHODS is empty" >&2
    exit 2
fi
for method in "${methods[@]}"; do
    if [[ ! " ${all_methods[*]} " == *" $method "* ]]; then
        echo "Unknown method: $method" >&2
        exit 2
    fi
done
declare -A seen_methods=()
for method in "${methods[@]}"; do
    if [[ -n "${seen_methods[$method]:-}" ]]; then
        echo "Duplicate method: $method" >&2
        exit 2
    fi
    seen_methods[$method]=1
done

python_bin="${ALLSAT_PYTHON_BIN:-$NRP_VENV/bin/python}"
solver_source="${TABULAR_ALLSAT_SOURCE:-$NRP_NATIVE_HOME/src/tabularAllSAT}"
solver_bin="${TABULAR_ALLSAT_BIN:-$solver_source/cdcl-vsads/solver}"
among_nurse_bin="${ALLSAT_AMONG_NURSE_BIN:-$SRC_PATH/Compare_NRP/CPLEX-For-NRP/CP/cpp_model/MiniCP/master/build/amongNurse}"
picat_bin="${ALLSAT_PICAT_BIN:-picat}"
timeout_s="${ALLSAT_TIMEOUT_S:-300}"
# Leave 6 GiB of physical RAM for Ubuntu and background processes by default.
if [[ -n "${ALLSAT_MEMORY_MB:-}" ]]; then
    memory_mb="$ALLSAT_MEMORY_MB"
else
    total_memory_mb="$(awk '/^MemTotal:/ {printf "%d\n", $2 / 1024; exit}' /proc/meminfo)"
    memory_mb="$((total_memory_mb - 6144))"
fi
output_root="${ALLSAT_OUTPUT_ROOT:-$SRC_PATH/tmp/amongNurse-allsat}"

if [[ ! -x "$python_bin" ]]; then
    echo "Missing Python: $python_bin (set NRP_VENV or ALLSAT_PYTHON_BIN)" >&2
    exit 2
fi
if [[ ! "$timeout_s" =~ ^[1-9][0-9]*$ || ! "$memory_mb" =~ ^[1-9][0-9]*$ ]]; then
    echo "ALLSAT_TIMEOUT_S and ALLSAT_MEMORY_MB must be positive integers" >&2
    exit 2
fi
for method in "${methods[@]}"; do
    if [[ "$method" == ladder || "$method" == de || "$method" == pblib_bdd-pblib_bdd ]]; then
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
        break
    fi
done

method_label() {
    case "$1" in
        ladder) echo "TabularAllSAT Ladder (staircase-binomial)" ;;
        pblib_bdd-pblib_bdd) echo "TabularAllSAT pblib_bdd-pblib_bdd" ;;
        de) echo "TabularAllSAT DE (pblib_bdd-binomial)" ;;
        sat_g421_*) echo "PySAT g421 (${1#sat_g421_})" ;;
        classic) echo "MiniCPP Classic" ;;
        amongMDD2) echo "MiniCPP amongMDD2" ;;
        seqMDD2) echo "MiniCPP seqMDD2" ;;
        *) echo "$1" ;;
    esac
}

show_result() {
    local prefix="$run_dir/${1}_C${2}_H${3}" status_override="${4:-}"
    "$python_bin" -B - "$prefix" "$status_override" <<'PY'
import json
from pathlib import Path
import re
import sys

prefix = Path(sys.argv[1])
override = sys.argv[2]
report = Path(str(prefix) + ".json")
data = json.loads(report.read_text()) if report.is_file() else {}
status = override or data.get("status", "error")
labels = {"complete": "OK", "timeout": "TIMEOUT", "count_mismatch": "COUNT_MISMATCH",
          "parse_error": "NO_COUNT", "error": "ERROR"}

def seconds(value):
    return f"{float(value):.3f}s" if value is not None else "-"

def number(value):
    return f"{int(value):,}" if value is not None else "-"

runlim_file = Path(str(prefix) + ".runlim.txt")
runlim = runlim_file.read_text(errors="replace") if runlim_file.is_file() else ""
def resource(name):
    match = re.search(r'^\[runlim\] ' + name + r':\s*([0-9.]+)', runlim, re.M)
    return float(match.group(1)) if match else None

gnu_time_file = Path(str(prefix) + ".gnu_time.txt")
times = re.findall(r'^([0-9]+(?:\.[0-9]+)?)\s*$', gnu_time_file.read_text(), re.M) if gnu_time_file.is_file() else []
gnu_wall = float(times[-1]) if times else None
ram = resource("space") if resource("samples") else None
print(f"    {labels.get(status, status)} | solutions: {number(data.get('reported_solutions'))} | "
      f"elapsed: {seconds(gnu_wall)} | peak RAM: {f'{ram:.1f} MB' if ram is not None else '-'}", flush=True)
if status != "complete":
    stderr_file = Path(str(prefix) + ".stderr.txt")
    error_log = stderr_file if stderr_file.is_file() and stderr_file.stat().st_size else runlim_file
    print(f"    Error log: {error_log.name}; report: {report.name} (in output dir above)", flush=True)
PY
}

run_legacy() {
    local method="$1" class_id="$2" horizon="$3" expected_count="$4"
    local prefix="${method}_C${class_id}_H${horizon}"
    local stdout_file="$run_dir/$prefix.stdout.txt"
    local stderr_file="$run_dir/$prefix.stderr.txt"
    local runlim_file="$run_dir/$prefix.runlim.txt"
    local gnu_time_file="$run_dir/$prefix.gnu_time.txt"
    local exit_file="$run_dir/$prefix.exit_code.txt"
    local report="$run_dir/$prefix.json"
    local exit_code runlim_code encoding
    local -a command

    case "$method" in
        sat_g421_*)
            encoding="${method#sat_g421_}"
            command=("$python_bin" -B "$SRC_PATH/src/test/NRP_2010.py" "$horizon" "$class_id" "$encoding" g421)
            ;;
        classic|amongMDD2|seqMDD2)
            local mode=0 n=0 d=2 max_p=0
            if [[ "$method" == amongMDD2 ]]; then mode=1; n=3; d=3; max_p=1; fi
            if [[ "$method" == seqMDD2 ]]; then mode=2; n=3; d=3; max_p=1; fi
            command=("$among_nurse_bin" -w64 -m"$mode" -r5 -i10 -c"$class_id" -h"$horizon"
                -n"$n" -na1 -d"$d" -ca1 -a1 -e1 -p0 -t3 -maxP"$max_p" -minP"$max_p" -wP0 -j1)
            ;;
        CPLEX_CP)
            command=("$python_bin" -B "$SRC_PATH/Compare_NRP_2010/CPLEX/CP/cp_model.py" "$horizon" "$class_id")
            ;;
        CPLEX_MP)
            command=("$python_bin" -B "$SRC_PATH/Compare_NRP_2010/CPLEX/MP/mp_model.py" "$horizon" "$class_id")
            ;;
        Gurobi)
            command=("$python_bin" -B "$SRC_PATH/Compare_NRP_2010/Gurobi/gurobi_model.py" "$horizon" "$class_id")
            ;;
        Picat)
            command=("$picat_bin" "$SRC_PATH/Compare_NRP_2010/Picat/sample.pi" "$class_id" "$horizon" 0)
            ;;
    esac

    # runlim returns its own status, even when the child fails. The small shell
    # records the actual child exit code before runlim exits.
    if /usr/bin/time -f '%e' -o "$gnu_time_file" \
            runlim -o "$runlim_file" -r "$((timeout_s + 60))" -s "$memory_mb" \
            bash -c '"$@"; code=$?; printf "%s\n" "$code" > "$0"; exit "$code"' \
            "$exit_file" timeout --foreground --signal=TERM --kill-after=5s "${timeout_s}s" "${command[@]}" \
            > "$stdout_file" 2> "$stderr_file"; then
        runlim_code=0
    else
        runlim_code=$?
    fi
    if [[ -s "$exit_file" ]]; then
        exit_code="$(<"$exit_file")"
    elif ((runlim_code != 0)); then
        exit_code="$runlim_code"
    else
        exit_code=125
    fi

    # The legacy programs print a final `solns` line; retain their own time in ms
    # alongside runlim wall/CPU/memory so it cannot be confused with AllSAT time.
    "$python_bin" -B - "$method" "$class_id" "$horizon" "$exit_code" "$expected_count" \
        "$stdout_file" "$stderr_file" "$runlim_file" "$report" "${command[@]}" <<'PY'
import json
from pathlib import Path
import re
import sys

method, class_id, horizon, exit_code, expected, stdout, stderr, runlim, report, *command = sys.argv[1:]
output = Path(stdout).read_text(errors="replace")
resources = Path(runlim).read_text(errors="replace")

def last_number(name):
    matches = re.findall(r'^\s*"?' + re.escape(name) + r'"?\s*:\s*(\d+)\b', output, re.M)
    return int(matches[-1]) if matches else None

def resource(name, unit=""):
    match = re.search(r'^\[runlim\] ' + name + r':\s*([0-9.]+)' + unit, resources, re.M)
    return float(match.group(1)) if match else None

solutions = last_number("solns")
code = int(exit_code)
expected = int(expected) if expected else None
status = "timeout" if code == 124 else "error" if code else "parse_error" if solutions is None else "complete"
if status == "complete" and expected is not None and solutions != expected:
    status = "count_mismatch"
result = {
    "status": status, "method": method, "class_id": int(class_id), "horizon": int(horizon),
    "reported_solutions": solutions, "expected_solutions": expected, "exit_code": code,
    "reported_time_ms": last_number("time"), "reported_first_solution_ms": last_number("timeToFirstSol"),
    "runlim_real_s": resource("real"), "runlim_cpu_s": resource("time"),
    "runlim_space_mb": resource("space"), "command": command,
    "stdout_file": stdout, "stderr_file": stderr, "runlim_file": runlim,
}
if method.startswith("sat_g421_"):
    result["encoding"] = method.removeprefix("sat_g421_")
    result["solver"] = "g421"
Path(report).write_text(json.dumps(result, indent=2) + "\n")
raise SystemExit(0 if status == "complete" else 1)
PY
}

mkdir -p "$output_root"
run_dir="$(mktemp -d "$output_root/$(date +%Y%m%d_%H%M%S)_XXXXXX")"
total_runs=$((${#classes[@]} * ${#horizons[@]} * ${#methods[@]}))
run_number=0
echo "Output dir: $run_dir"
echo "Plan: C=[${classes[*]}], H=[${horizons[*]}], methods=${#methods[@]}, runs=$total_runs"
echo "Per-run limits: ${timeout_s}s; ${memory_mb} MB RAM"
echo "Elapsed = GNU wall time for the full run; peak RAM is from runlim."
if [[ "${ALLSAT_VALIDATE_MODELS:-0}" == 1 ]]; then validation_label=ON; else validation_label=OFF; fi
echo "Other timings and CPU are in summary.csv. AllSAT model validation: $validation_label."
failed=0
for class_id in "${classes[@]}"; do
    for horizon in "${horizons[@]}"; do
        baseline_count=""
        for method in "${methods[@]}"; do
            run_number=$((run_number + 1))
            printf '[%d/%d] C=%s H=%s | %s: START\n' \
                "$run_number" "$total_runs" "$class_id" "$horizon" "$(method_label "$method")"
            if [[ "$method" != ladder && "$method" != de && "$method" != pblib_bdd-pblib_bdd ]]; then
                if ! run_legacy "$method" "$class_id" "$horizon" "$baseline_count"; then
                    failed=$((failed + 1))
                fi
                show_result "$method" "$class_id" "$horizon"
                continue
            fi
            # Keep the projected TabularAllSAT execution and validation path.
            args=(
                --method "$method" --class-id "$class_id" --horizon "$horizon"
                --solver-bin "$solver_bin" --output-dir "$run_dir"
                --timeout-s "$timeout_s"
            )
            if [[ "${ALLSAT_VALIDATE_MODELS:-0}" == 1 ]]; then args+=(--validate-models); fi
            report="$run_dir/${method}_C${class_id}_H${horizon}.json"
            gnu_time_file="$run_dir/${method}_C${class_id}_H${horizon}.gnu_time.txt"
            if /usr/bin/time -f '%e' -o "$gnu_time_file" \
                    runlim -r "$((timeout_s + 60))" -s "$memory_mb" \
                    "$python_bin" -B "$SRC_PATH/src/test/NRP_2010_allsat.py" "${args[@]}" \
                    > "$run_dir/${method}_C${class_id}_H${horizon}.stdout.txt" \
                    2> "$run_dir/${method}_C${class_id}_H${horizon}.runlim.txt"; then
                command_ok=1
            else
                command_ok=0
            fi
            status_override=""
            if ((command_ok == 0)) || [[ ! -s "$report" ]] || ! grep -q '"status": "complete"' "$report"; then
                failed=$((failed + 1))
                if ((command_ok == 0)); then status_override="error"; fi
            else
                count="$("$python_bin" -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["reported_solutions"])' "$report")"
                if [[ -z "$baseline_count" ]]; then
                    baseline_count="$count"
                elif [[ "$count" != "$baseline_count" ]]; then
                    failed=$((failed + 1))
                    status_override="count_mismatch"
                    echo "    Count mismatch: expected $baseline_count, got $count." >&2
                fi
            fi
            show_result "$method" "$class_id" "$horizon" "$status_override"
        done
    done
done
"$python_bin" -B - "$run_dir" <<'PY'
import csv
import json
from pathlib import Path
import re
import sys

run_dir = Path(sys.argv[1])
columns = ("method", "class_id", "horizon", "status", "reported_solutions", "encoding", "solver", "validation",
           "encoding_wall_s", "solver_wall_s_including_pipe", "reported_time_ms",
           "reported_first_solution_ms", "runlim_real_s", "gnu_time_real_s", "runlim_cpu_s",
           "runlim_space_mb", "gnu_time_file", "report")
with (run_dir / "summary.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for report in sorted(run_dir.glob("*.json")):
        data = json.loads(report.read_text())
        row = {key: data.get(key) for key in columns}
        if "solver_bin" in data:
            row["solver"] = "TabularAllSAT"
        row["report"] = str(report)
        log = run_dir / (report.stem + ".runlim.txt")
        if log.is_file():
            content = log.read_text(errors="replace")
            for field, label in (("runlim_real_s", "real"), ("runlim_cpu_s", "time"),
                                 ("runlim_space_mb", "space")):
                match = re.search(r'^\[runlim\] ' + label + r':\s*([0-9.]+)', content, re.M)
                if match:
                    row[field] = float(match.group(1))
        gnu_time_file = run_dir / (report.stem + ".gnu_time.txt")
        if gnu_time_file.is_file():
            row["gnu_time_file"] = str(gnu_time_file)
            matches = re.findall(r'^([0-9]+(?:\.[0-9]+)?)\s*$', gnu_time_file.read_text(), re.M)
            if matches:
                row["gnu_time_real_s"] = float(matches[-1])
        writer.writerow(row)
PY
echo "Successful runs: $((total_runs - failed))/$total_runs. Summary: $run_dir/summary.csv"
if ((failed > 0)); then
    echo "$failed failed or mismatched runs; see logs in $run_dir" >&2
    exit 1
fi
