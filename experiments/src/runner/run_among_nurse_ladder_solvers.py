#!/usr/bin/env python3
"""Python runner for the amongNurse Ladder AllSAT solver comparison.

The benchmarked command has the same scope as in the shell runner::

    timeout -> Python method driver

``python_subprocess_wall_s`` measures that command with ``perf_counter_ns``.
``python_runner_wall_s`` additionally includes the surrounding runlim process
and is retained only as a diagnostic for wrapper overhead.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import time


ALL_METHODS = (
    "g421-legacy-enum-models",
    "g421-projected",
    "cadical195-projected",
    "tabularallsat",
)
VALID_HORIZONS = (40, 50, 60, 70, 80)
TABULAR_ALLSAT_COMMIT = "ad4a071310581990b7834f1f076ccfb54d592bbf"


def write_text_atomic(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def timed_child(argv: list[str]) -> int:
    """Measure one child command from immediately before spawn through exit."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--elapsed-file", type=Path, required=True)
    parser.add_argument("--exit-file", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("timed child requires a command after --")

    started_ns = time.perf_counter_ns()
    completed = subprocess.run(command, check=False)
    elapsed_ns = time.perf_counter_ns() - started_ns
    return_code = completed.returncode if completed.returncode >= 0 else 128 - completed.returncode
    write_text_atomic(args.elapsed_file, f"{elapsed_ns / 1_000_000_000:.9f}\n")
    write_text_atomic(args.exit_file, f"{return_code}\n")
    return return_code


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare four AllSAT backends on the same Ladder amongNurse CNF."
    )
    parser.add_argument("--grid", action="store_true", help="run all 15 C/H instances")
    parser.add_argument(
        "--classes",
        nargs="+",
        type=int,
        choices=(1, 2, 3),
        metavar="C",
        help="classes to run; omitted --horizons means all five horizons",
    )
    parser.add_argument(
        "--horizons",
        nargs="+",
        type=int,
        choices=VALID_HORIZONS,
        metavar="H",
        help="horizons to run; omitted --classes means all three classes",
    )
    parser.add_argument("class_id", nargs="?", type=int, choices=(1, 2, 3))
    parser.add_argument("horizon", nargs="?", type=int, choices=VALID_HORIZONS)
    args = parser.parse_args(argv)
    selected = args.classes is not None or args.horizons is not None
    positional = args.class_id is not None or args.horizon is not None
    if args.grid and (selected or positional):
        parser.error("--grid cannot be combined with class or horizon selections")
    if (args.class_id is None) != (args.horizon is None):
        parser.error("provide both CLASS and HORIZON, or neither")
    if selected and positional:
        parser.error("--classes/--horizons cannot be combined with CLASS HORIZON")
    if args.classes is not None and len(set(args.classes)) != len(args.classes):
        parser.error("--classes contains a duplicate class")
    if args.horizons is not None and len(set(args.horizons)) != len(args.horizons):
        parser.error("--horizons contains a duplicate horizon")
    return args


def environment_positive_integer(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return positive_integer(raw)
    except (TypeError, ValueError, argparse.ArgumentTypeError) as error:
        raise SystemExit(f"{name} must be a positive integer: {raw!r}") from error


def total_memory_mb() -> int:
    with Path("/proc/meminfo").open(encoding="ascii") as stream:
        for line in stream:
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) // 1024
    raise SystemExit("cannot read MemTotal from /proc/meminfo")


def selected_methods() -> tuple[str, ...]:
    raw = os.environ.get("LADDER_SOLVER_METHODS")
    methods = tuple(raw.split()) if raw is not None else ALL_METHODS
    if not methods:
        raise SystemExit("LADDER_SOLVER_METHODS is empty")
    unknown = [method for method in methods if method not in ALL_METHODS]
    if unknown:
        raise SystemExit(f"unknown method: {unknown[0]}")
    if len(set(methods)) != len(methods):
        raise SystemExit("LADDER_SOLVER_METHODS contains a duplicate method")
    return methods


def read_last_float(path: Path) -> float | None:
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in reversed(lines):
        try:
            return float(line.strip())
        except ValueError:
            continue
    return None


def parse_runlim(path: Path) -> tuple[float | None, float | None]:
    if not path.is_file():
        return None, None
    content = path.read_text(encoding="utf-8", errors="replace")
    values: dict[str, float | None] = {"time": None, "space": None}
    for field in values:
        match = re.search(rf"^\[runlim\] {field}:\s*([0-9.]+)", content, re.MULTILINE)
        if match:
            values[field] = float(match.group(1))
    return values["time"], values["space"]


def create_summary(run_dir: Path) -> bool:
    columns = (
        "method",
        "class_id",
        "horizon",
        "status",
        "reported_solutions",
        "solver",
        "enumeration_mode",
        "n_vars",
        "n_clauses_initial",
        "encoding_wall_s",
        "cnf_write_wall_s",
        "solver_wall_s",
        "total_internal_wall_s",
        "python_subprocess_wall_s",
        "python_runner_wall_s",
        "runlim_cpu_s",
        "runlim_space_mb",
        "projected_blocking_clauses",
        "full_model_blocking_clauses",
        "validation",
        "report",
    )
    rows: list[dict] = []
    for report_path in sorted(run_dir.glob("*.json")):
        data = json.loads(report_path.read_text(encoding="utf-8"))
        row = {key: data.get(key) for key in columns}
        row["report"] = str(report_path)
        stem = report_path.with_suffix("")
        row["python_subprocess_wall_s"] = read_last_float(
            Path(f"{stem}.python_time.txt")
        )
        row["python_runner_wall_s"] = read_last_float(
            Path(f"{stem}.runner_time.txt")
        )
        row["runlim_cpu_s"], row["runlim_space_mb"] = parse_runlim(
            Path(f"{stem}.runlim.txt")
        )
        rows.append(row)

    groups: dict[tuple[int, int], set[int]] = {}
    for row in rows:
        if row["status"] == "complete":
            key = (row["class_id"], row["horizon"])
            groups.setdefault(key, set()).add(row["reported_solutions"])
    mismatches = {key: counts for key, counts in groups.items() if len(counts) > 1}
    for (class_id, horizon), counts in sorted(mismatches.items()):
        print(f"Count mismatch for C={class_id}, H={horizon}: {sorted(counts)}", file=sys.stderr)
    for row in rows:
        if (row["class_id"], row["horizon"]) in mismatches and row["status"] == "complete":
            row["status"] = "count_mismatch"

    with (run_dir / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return not mismatches


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[3]
    home = Path.home()
    nrp_venv = Path(os.environ.get("NRP_VENV", repo_root / ".venv"))
    native_home = Path(
        os.environ.get("NRP_NATIVE_HOME", home / ".local/opt/sequenceconstraint")
    )
    python_bin = Path(
        os.environ.get("LADDER_SOLVER_PYTHON_BIN", nrp_venv / "bin/python")
    )
    driver = repo_root / "experiments/src/methods/among_nurse_ladder_solvers.py"
    solver_source = Path(
        os.environ.get("TABULAR_ALLSAT_SOURCE", native_home / "src/tabularAllSAT")
    )
    explicit_solver_bin = os.environ.get("TABULAR_ALLSAT_BIN")
    solver_bin = Path(explicit_solver_bin) if explicit_solver_bin else solver_source / "cdcl-vsads/solver"
    timeout_s = environment_positive_integer("LADDER_SOLVER_TIMEOUT_S", 300)
    memory_mb = environment_positive_integer(
        "LADDER_SOLVER_MEMORY_MB", max(total_memory_mb() - 6144, 1024)
    )
    output_root = Path(
        os.environ.get(
            "LADDER_SOLVER_OUTPUT_ROOT",
            repo_root / "experiments/runs/amongNurse-ladder-solvers-python",
        )
    )
    methods = selected_methods()

    if args.grid:
        classes, horizons = (1, 2, 3), VALID_HORIZONS
    elif args.classes is not None or args.horizons is not None:
        classes = tuple(args.classes) if args.classes is not None else (1, 2, 3)
        horizons = tuple(args.horizons) if args.horizons is not None else VALID_HORIZONS
    elif args.class_id is not None:
        classes, horizons = (args.class_id,), (args.horizon,)
    else:
        classes, horizons = (2,), (40,)

    runlim = shutil.which("runlim")
    timeout = shutil.which("timeout")
    if runlim is None:
        raise SystemExit("missing runlim")
    if timeout is None:
        raise SystemExit("missing GNU timeout")
    if not python_bin.is_file() or not os.access(python_bin, os.X_OK):
        raise SystemExit(f"missing Python: {python_bin}")
    if not driver.is_file():
        raise SystemExit(f"missing driver: {driver}")
    if "tabularallsat" in methods:
        if not solver_bin.is_file() or not os.access(solver_bin, os.X_OK):
            raise SystemExit(f"missing TabularAllSAT: {solver_bin} (see docs/TABULAR_ALLSAT.md)")
        if explicit_solver_bin is None:
            actual = subprocess.run(
                ["git", "-C", str(solver_source), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            if actual != TABULAR_ALLSAT_COMMIT:
                raise SystemExit(
                    f"wrong TabularAllSAT commit: {actual} (expected {TABULAR_ALLSAT_COMMIT})"
                )

    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_root / f"{stamp}_{secrets.token_hex(3)}"
    run_dir.mkdir()
    total_runs = len(classes) * len(horizons) * len(methods)
    run_number = 0
    failed = 0

    print(f"Output dir: {run_dir}")
    print(
        f"Plan: C=[{' '.join(map(str, classes))}], H=[{' '.join(map(str, horizons))}], "
        f"methods=[{' '.join(methods)}], runs={total_runs}"
    )
    print(f"Per-run limits: {timeout_s}s; {memory_mb} MB RAM")
    print(
        "Elapsed metric: Python perf_counter_ns wall time for the complete method process; "
        "runlim overhead is excluded."
    )

    validate_models = os.environ.get("LADDER_SOLVER_VALIDATE_MODELS", "0") == "1"
    for class_id in classes:
        for horizon in horizons:
            for method in methods:
                run_number += 1
                prefix = run_dir / f"ladder_{method.replace('-', '_')}_C{class_id}_H{horizon}"
                stdout_file = Path(f"{prefix}.stdout.txt")
                runlim_file = Path(f"{prefix}.runlim.txt")
                python_time_file = Path(f"{prefix}.python_time.txt")
                runner_time_file = Path(f"{prefix}.runner_time.txt")
                exit_file = Path(f"{prefix}.exit_code.txt")
                report = Path(f"{prefix}.json")

                driver_args = [
                    "--method", method,
                    "--class-id", str(class_id),
                    "--horizon", str(horizon),
                    "--output-dir", str(run_dir),
                    "--timeout-s", str(timeout_s),
                ]
                if method == "tabularallsat":
                    driver_args.extend(("--solver-bin", str(solver_bin)))
                if validate_models:
                    driver_args.append("--validate-models")

                benchmark_command = [
                    timeout,
                    "--foreground",
                    "--signal=TERM",
                    "--kill-after=5s",
                    f"{timeout_s}s",
                    str(python_bin),
                    "-B",
                    str(driver),
                    *driver_args,
                ]
                command = [
                    runlim,
                    "-o", str(runlim_file),
                    "-r", str(timeout_s + 60),
                    "-s", str(memory_mb),
                    sys.executable,
                    "-B",
                    str(Path(__file__).resolve()),
                    "--_timed-child",
                    "--elapsed-file", str(python_time_file),
                    "--exit-file", str(exit_file),
                    "--",
                    *benchmark_command,
                ]

                print(
                    f"[{run_number}/{total_runs}] C={class_id} H={horizon} | {method}: START",
                    flush=True,
                )
                wrapper_started_ns = time.perf_counter_ns()
                with stdout_file.open("w", encoding="utf-8", newline="\n") as output:
                    completed = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, check=False)
                wrapper_elapsed_s = (time.perf_counter_ns() - wrapper_started_ns) / 1_000_000_000
                write_text_atomic(runner_time_file, f"{wrapper_elapsed_s:.9f}\n")

                child_code = 125
                if exit_file.is_file():
                    try:
                        child_code = int(exit_file.read_text(encoding="utf-8").strip())
                    except ValueError:
                        pass
                if completed.returncode != 0 or child_code != 0 or not report.is_file():
                    failed += 1
                    print(
                        f"    ERROR/TIMEOUT | child={child_code} runlim={completed.returncode} "
                        f"| log: {stdout_file}"
                    )
                    continue

                data = json.loads(report.read_text(encoding="utf-8"))
                elapsed = read_last_float(python_time_file)
                elapsed_text = f"{elapsed:.6f}s" if elapsed is not None else "missing"
                print(
                    f"    {data['status'].upper()} | solutions: {data['reported_solutions']:,} "
                    f"| elapsed: {elapsed_text} | solver: {data['solver']}"
                )

    if not create_summary(run_dir):
        failed += 1
    print(f"Completed: {total_runs - failed}/{total_runs}. Summary: {run_dir / 'summary.csv'}")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--_timed-child":
        raise SystemExit(timed_child(sys.argv[2:]))
    raise SystemExit(main(sys.argv[1:]))
