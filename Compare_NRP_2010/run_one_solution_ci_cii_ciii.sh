#!/usr/bin/env bash
# Compatibility entrypoint for the Python perf_counter_ns runner.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${ONE_SOLUTION_PYTHON_BIN:-$repo_root/.venv/bin/python}"

if [[ ! -x "$python_bin" ]]; then
    echo "Missing Python: $python_bin (set ONE_SOLUTION_PYTHON_BIN)" >&2
    exit 2
fi

exec "$python_bin" -B \
    "$repo_root/Compare_NRP_2010/run_one_solution_ci_cii_ciii.py" "$@"
