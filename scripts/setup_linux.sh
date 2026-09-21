#!/usr/bin/env bash
# Run with bash scripts/setup_linux.sh from any working directory.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON_BIN:-python3}"
venv_dir="${NRP_VENV:-$HOME/.venvs/sequenceconstraint}"
"$python_bin" -c 'import sys; assert sys.version_info >= (3, 12), "Use Python 3.12 or newer for this Linux development profile"'
for program in gcc g++ clang++ make cmake runlim; do
    if ! command -v "$program" >/dev/null 2>&1; then
        printf 'Missing %s; install the apt dependencies listed in docs/WSL_ENVIRONMENT.md\n' "$program" >&2
        exit 1
    fi
done
if [[ ! -e "$venv_dir" ]]; then
    "$python_bin" -m venv "$venv_dir"
elif [[ ! -x "$venv_dir/bin/python" ]]; then
    printf 'Existing path is not a Linux virtualenv: %s\n' "$venv_dir" >&2
    exit 1
fi
"$venv_dir/bin/python" -c 'import sys; assert sys.platform == "linux" and sys.version_info >= (3, 12), "The virtualenv must use Linux Python 3.12+"'
requirements="$repo_dir/requirements-linux.lock.txt"
if [[ ! -f "$requirements" ]]; then
    requirements="$repo_dir/requirements-linux.in"
fi
"$venv_dir/bin/python" -m pip install --upgrade pip wheel
"$venv_dir/bin/python" -m pip install -r "$requirements"
"$venv_dir/bin/python" -m pip check
printf 'Linux interpreter: %s/bin/python\n' "$venv_dir"
