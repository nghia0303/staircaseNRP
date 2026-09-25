#!/usr/bin/env python3
"""Run the full amongNurse one-solution comparison.

Every method is launched as a fresh process.  The primary metric,
``method_wall_s``, is measured with ``time.perf_counter_ns()`` around the same
boundary for every method::

    timeout -> method process -> process exit

``runlim`` is outside that measured boundary.  It enforces the time and memory
limits and records resource diagnostics without adding its own startup and
shutdown overhead to ``method_wall_s``.

The previous shell runner is intentionally kept alongside this file so old
experiments remain reproducible.
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
import statistics
import subprocess
import sys
from typing import Iterable


ALL_METHODS = (
    "sat_g421_staircase-binomial",
    "sat_g421_pblib_bdd-pblib_bdd",
    "sat_g421_pblib_bdd-binomial",
    "sat_cadical195_staircase-binomial",
    "sat_cadical195_pblib_bdd-pblib_bdd",
    "sat_cadical195_pblib_bdd-binomial",
    "sat_cadical300_staircase-binomial",
    "sat_cadical300_pblib_bdd-pblib_bdd",
    "sat_cadical300_pblib_bdd-binomial",
    "classic",
    "amongMDD2",
    "seqMDD2",
    "CPLEX_CP",
    "CPLEX_MP",
    "Gurobi",
    "Picat",
)
SAT_ENCODINGS = (
    "staircase-binomial",
    "pblib_bdd-pblib_bdd",
    "pblib_bdd-binomial",
)
PRIVATE_METHODS = tuple(
    f"sat_pysolvers_{backend}_{encoding}"
    for backend in ("glucose421", "cadical195", "cadical300")
    for encoding in SAT_ENCODINGS
)
KNOWN_METHODS = ALL_METHODS + PRIVATE_METHODS
VALID_HORIZONS = (40, 50, 60, 70, 80)
SUMMARY_COLUMNS = (
    "method",
    "class_id",
    "horizon",
    "repetition",
    "status",
    "reported_solutions",
    "expected_solutions",
    "encoding",
    "solver",
    "solver_api",
    "native_backend",
    "method_wall_s",
    "timing_boundary",
    "timer",
    "reported_time_ms",
    "reported_first_solution_ms",
    "runlim_real_s",
    "runlim_samples",
    "runlim_cpu_s",
    "runlim_space_mb",
    "exit_code",
    "method_time_file",
    "stdout_file",
    "stderr_file",
    "runlim_file",
    "report",
)
TIMING_BOUNDARY = "timeout_spawn_to_method_process_exit"
TIMER = "time.perf_counter_ns"


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


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


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run amongNurse one-solution methods with a uniform fresh-process "
            "perf_counter_ns wall-time boundary."
        )
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--grid",
        action="store_true",
        help="run C-I, C-II, and C-III for H=40,50,60,70,80 (default)",
    )
    selection.add_argument(
        "--ci-cii",
        action="store_true",
        help="run C-I and C-II for H=40,50,60,70,80",
    )
    parser.add_argument("class_id", nargs="?", type=int, choices=(1, 2, 3))
    parser.add_argument("horizon", nargs="?", type=int, choices=VALID_HORIZONS)
    parser.add_argument(
        "--repetitions",
        type=positive_integer,
        default=environment_positive_integer("ONE_SOLUTION_REPETITIONS", 1),
        help=(
            "fresh-process repetitions per method and instance; default: "
            "ONE_SOLUTION_REPETITIONS or 1"
        ),
    )
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="append all nine experimental direct-pysolvers methods",
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=KNOWN_METHODS,
        help="methods to run; default: ONE_SOLUTION_METHODS or the 16 public methods",
    )
    parser.add_argument(
        "--timeout-s",
        type=positive_integer,
        default=environment_positive_integer("ONE_SOLUTION_TIMEOUT_S", 300),
    )
    parser.add_argument(
        "--memory-mb",
        type=positive_integer,
        default=environment_positive_integer(
            "ONE_SOLUTION_MEMORY_MB", max(total_memory_mb() - 6144, 1024)
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="root for a new timestamped output directory",
    )
    args = parser.parse_args(argv)

    if (args.class_id is None) != (args.horizon is None):
        parser.error("provide both CLASS and HORIZON, or neither")
    if args.class_id is not None and (args.grid or args.ci_cii):
        parser.error("CLASS HORIZON cannot be combined with --grid or --ci-cii")
    return args


def choose_methods(args: argparse.Namespace) -> tuple[str, ...]:
    if args.methods is not None:
        methods = tuple(args.methods)
    else:
        raw = os.environ.get("ONE_SOLUTION_METHODS")
        methods = tuple(raw.split()) if raw is not None else ALL_METHODS
    if args.include_private:
        methods += tuple(method for method in PRIVATE_METHODS if method not in methods)
    if not methods:
        raise SystemExit("ONE_SOLUTION_METHODS is empty")
    unknown = [method for method in methods if method not in KNOWN_METHODS]
    if unknown:
        raise SystemExit(f"unknown method: {unknown[0]}")
    if len(set(methods)) != len(methods):
        raise SystemExit("method list contains a duplicate")
    return methods


def choose_instances(args: argparse.Namespace) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if args.class_id is not None:
        return (args.class_id,), (args.horizon,)
    if args.ci_cii:
        return (1, 2), VALID_HORIZONS
    return (1, 2, 3), VALID_HORIZONS


def build_environment(repo_root: Path) -> tuple[dict[str, str], Path, Path]:
    env = os.environ.copy()
    local_venv = repo_root / ".venv"
    default_venv = local_venv if (local_venv / "bin/python").is_file() else Path.home() / ".venvs/sequenceconstraint"
    nrp_venv = Path(env.get("NRP_VENV", default_venv)).expanduser().resolve()
    native_home = Path(
        env.get("NRP_NATIVE_HOME", Path.home() / ".local/opt/sequenceconstraint")
    ).expanduser().resolve()

    env["SRC_PATH"] = str(repo_root)
    env["NRP_VENV"] = str(nrp_venv)
    env["NRP_NATIVE_HOME"] = str(native_home)
    path_entries = (native_home / "bin", nrp_venv / "bin")
    env["PATH"] = os.pathsep.join(
        [str(path) for path in path_entries] + [env.get("PATH", "")]
    )
    env["PICAT_RUN_PATH"] = str(native_home / "bin/picat")
    env["AMONG_NURSE_SCRIPT"] = str(native_home / "bin/amongNurse")
    env["HADDOCK_CP_SCRIPT"] = str(native_home / "bin/sequenceNurse")
    env["HADDOCK_CP_SEQ_SCRIPT"] = str(native_home / "bin/sequenceNurseNew")

    cplex_dir = Path(
        env.get(
            "CPLEX_STUDIO_DIR",
            Path.home() / ".local/opt/ibm/ILOG/CPLEX_Studio2220",
        )
    ).expanduser()
    env["CPLEX_STUDIO_DIR"] = str(cplex_dir)
    cpo_bin_dir = cplex_dir / "cpoptimizer/bin/x86-64_linux"
    cplex_bin_dir = cplex_dir / "cplex/bin/x86-64_linux"
    cpo_executable = cpo_bin_dir / "cpoptimizer"
    if cpo_executable.is_file() and os.access(cpo_executable, os.X_OK):
        env["CPO_EXECUTABLE"] = str(cpo_executable)
        env["PATH"] = os.pathsep.join(
            (str(cpo_bin_dir), str(cplex_bin_dir), env["PATH"])
        )
    return env, nrp_venv, native_home


def executable_path(value: str, env: dict[str, str]) -> Path | None:
    candidate = Path(value).expanduser()
    if os.sep in value or candidate.is_absolute():
        # Keep a virtualenv Python symlink intact. Resolving it to
        # /usr/bin/python would lose the virtualenv site-packages at launch.
        return candidate.absolute() if candidate.is_file() and os.access(candidate, os.X_OK) else None
    found = shutil.which(value, path=env.get("PATH"))
    return Path(found).absolute() if found else None


def method_label(method: str) -> str:
    private_prefixes = (
        ("sat_pysolvers_glucose421_", "pysolvers private G421"),
        ("sat_pysolvers_cadical195_", "pysolvers private CaDiCaL 1.9.5"),
        ("sat_pysolvers_cadical300_", "pysolvers private CaDiCaL 3.0"),
    )
    for prefix, label in private_prefixes:
        if method.startswith(prefix):
            return f"{label} ({method.removeprefix(prefix)})"
    if method.startswith("sat_g421_"):
        return f"PySAT G421 ({method.removeprefix("sat_g421_")})"
    if method.startswith("sat_cadical195_"):
        return f"PySAT CaDiCaL 1.9.5 ({method.removeprefix("sat_cadical195_")})"
    if method.startswith("sat_cadical300_"):
        return f"PySAT CaDiCaL 3.0 ({method.removeprefix("sat_cadical300_")})"
    return {
        "classic": "MiniCPP Classic",
        "amongMDD2": "MiniCPP amongMDD2",
        "seqMDD2": "MiniCPP seqMDD2",
        "CPLEX_CP": "CPLEX CP",
        "CPLEX_MP": "CPLEX MP",
        "Gurobi": "Gurobi",
        "Picat": "Picat",
    }[method]


def sat_metadata(
    method: str,
) -> tuple[str | None, str | None, str | None, str | None]:
    methods = (
        ("sat_pysolvers_glucose421_", "g421", "glucose421", "pysolvers_private"),
        ("sat_pysolvers_cadical195_", "cadical195", "cadical195", "pysolvers_private"),
        ("sat_pysolvers_cadical300_", "cadical300", "cadical300", "pysolvers_private"),
        ("sat_g421_", "g421", "glucose421", "pysat_public"),
        ("sat_cadical195_", "cadical195", "cadical195", "pysat_public"),
        ("sat_cadical300_", "cadical300", "cadical300", "pysat_public"),
    )
    for prefix, solver, native_backend, solver_api in methods:
        if method.startswith(prefix):
            return (
                method.removeprefix(prefix),
                solver,
                native_backend,
                solver_api,
            )
    return None, None, None, None


def method_command(
    method: str,
    class_id: int,
    horizon: int,
    repo_root: Path,
    python_bin: Path,
    among_nurse_bin: Path,
    picat_bin: Path,
) -> tuple[
    list[str],
    str | None,
    str | None,
    str | None,
    str | None,
]:
    encoding, solver, native_backend, solver_api = sat_metadata(method)
    if solver_api == "pysolvers_private":
        return (
            [
                str(python_bin),
                "-B",
                str(repo_root / "src/test/NRP_2010_pysolvers_private.py"),
                str(horizon),
                str(class_id),
                encoding,
                solver,
            ],
            encoding,
            solver,
            native_backend,
            solver_api,
        )
    if solver_api == "pysat_public":
        return (
            [
                str(python_bin),
                "-B",
                str(repo_root / "src/test/NRP_2010.py"),
                str(horizon),
                str(class_id),
                encoding,
                solver,
                "false",
                "false",
                "5",
                "true",
            ],
            encoding,
            solver,
            native_backend,
            solver_api,
        )
    if method in ("classic", "amongMDD2", "seqMDD2"):
        mode, node_priority, candidate_priority, max_priority = {
            "classic": (0, 0, 2, 0),
            "amongMDD2": (1, 3, 3, 1),
            "seqMDD2": (2, 3, 3, 1),
        }[method]
        return (
            [
                str(among_nurse_bin),
                "-w64",
                f"-m{mode}",
                "-r5",
                "-i10",
                f"-c{class_id}",
                f"-h{horizon}",
                f"-n{node_priority}",
                "-na1",
                f"-d{candidate_priority}",
                "-ca1",
                "-a1",
                "-e1",
                "-p0",
                "-t3",
                f"-maxP{max_priority}",
                f"-minP{max_priority}",
                "-wP0",
                "-j1",
                "-so1",
            ],
            None,
            None,
            None,
            None,
        )
    if method == "CPLEX_CP":
        driver = repo_root / "Compare_NRP_2010/CPLEX/CP/cp_model.py"
        return [str(python_bin), "-B", str(driver), str(horizon), str(class_id), "true"], None, None, None, None
    if method == "CPLEX_MP":
        driver = repo_root / "Compare_NRP_2010/CPLEX/MP/mp_model.py"
        return [str(python_bin), "-B", str(driver), str(horizon), str(class_id), "true"], None, None, None, None
    if method == "Gurobi":
        driver = repo_root / "Compare_NRP_2010/Gurobi/gurobi_model.py"
        return [str(python_bin), "-B", str(driver), str(horizon), str(class_id), "true"], None, None, None, None
    if method == "Picat":
        driver = repo_root / "Compare_NRP_2010/Picat/sample.pi"
        return [str(picat_bin), str(driver), str(class_id), str(horizon), "1"], None, None, None, None
    raise AssertionError(f"unhandled method: {method}")

def last_number(text: str, name: str) -> float | None:
    matches = re.findall(
        r'^\s*"?' + re.escape(name) + r'"?\s*:\s*([0-9]+(?:\.[0-9]+)?)\b',
        text,
        re.MULTILINE,
    )
    return float(matches[-1]) if matches else None


def runlim_value(text: str, name: str) -> float | None:
    match = re.search(
        r"^\[runlim\] " + re.escape(name) + r":\s*([0-9.]+)",
        text,
        re.MULTILINE,
    )
    return float(match.group(1)) if match else None


def read_float(path: Path) -> float | None:
    if not path.is_file():
        return None
    try:
        return float(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def read_integer(path: Path) -> int | None:
    if not path.is_file():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def write_json_atomic(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def load_reports(run_dir: Path) -> list[dict]:
    reports = []
    for path in sorted(run_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["report"] = str(path)
        reports.append(data)
    return reports


def write_summaries(run_dir: Path, repetitions: int) -> tuple[int, int]:
    reports = load_reports(run_dir)
    with (run_dir / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        for data in reports:
            writer.writerow({key: data.get(key) for key in SUMMARY_COLUMNS})

    groups: dict[tuple[str, int, int], list[dict]] = {}
    for data in reports:
        key = (data["method"], data["class_id"], data["horizon"])
        groups.setdefault(key, []).append(data)

    aggregate_columns = (
        "method",
        "class_id",
        "horizon",
        "solver_api",
        "native_backend",
        "status",
        "repetitions_requested",
        "runs_recorded",
        "complete_runs",
        "reported_solutions",
        "method_wall_median_s",
        "method_wall_q1_s",
        "method_wall_q3_s",
        "method_wall_min_s",
        "method_wall_max_s",
        "reported_time_median_ms",
        "runlim_space_max_mb",
    )
    with (run_dir / "summary_aggregate.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=aggregate_columns)
        writer.writeheader()
        for (method, class_id, horizon), rows in sorted(groups.items()):
            complete = [row for row in rows if row.get("status") == "complete"]
            walls = [float(row["method_wall_s"]) for row in complete if row.get("method_wall_s") is not None]
            internals = [float(row["reported_time_ms"]) for row in complete if row.get("reported_time_ms") is not None]
            memories = [float(row["runlim_space_mb"]) for row in complete if row.get("runlim_space_mb") is not None]
            counts = {row.get("reported_solutions") for row in complete}
            status = "complete" if len(complete) == repetitions else "incomplete"
            writer.writerow(
                {
                    "method": method,
                    "class_id": class_id,
                    "horizon": horizon,
                    "solver_api": rows[0].get("solver_api"),
                    "native_backend": rows[0].get("native_backend"),
                    "status": status,
                    "repetitions_requested": repetitions,
                    "runs_recorded": len(rows),
                    "complete_runs": len(complete),
                    "reported_solutions": next(iter(counts)) if len(counts) == 1 else None,
                    "method_wall_median_s": round(statistics.median(walls), 9) if walls else None,
                    "method_wall_q1_s": round(percentile(walls, 0.25), 9) if walls else None,
                    "method_wall_q3_s": round(percentile(walls, 0.75), 9) if walls else None,
                    "method_wall_min_s": min(walls) if walls else None,
                    "method_wall_max_s": max(walls) if walls else None,
                    "reported_time_median_ms": statistics.median(internals) if internals else None,
                    "runlim_space_max_mb": max(memories) if memories else None,
                }
            )

    completed = sum(data.get("status") == "complete" for data in reports)
    return completed, len(reports)


def rotated(values: tuple[str, ...], offset: int) -> Iterable[str]:
    if not values:
        return values
    pivot = offset % len(values)
    return values[pivot:] + values[:pivot]


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    methods = choose_methods(args)
    classes, horizons = choose_instances(args)
    env, nrp_venv, native_home = build_environment(repo_root)

    python_value = os.environ.get(
        "ONE_SOLUTION_PYTHON_BIN", str(nrp_venv / "bin/python")
    )
    python_bin = executable_path(python_value, env)
    if python_bin is None:
        raise SystemExit(
            f"missing Python: {python_value} "
            "(set NRP_VENV or ONE_SOLUTION_PYTHON_BIN)"
        )

    among_value = os.environ.get(
        "ONE_SOLUTION_AMONG_NURSE_BIN",
        str(
            repo_root
            / "Compare_NRP/CPLEX-For-NRP/CP/cpp_model/MiniCP/master/build/amongNurse"
        ),
    )
    among_nurse_bin = executable_path(among_value, env)
    if any(method in ("classic", "amongMDD2", "seqMDD2") for method in methods):
        if among_nurse_bin is None:
            raise SystemExit(f"missing amongNurse: {among_value}")
    else:
        among_nurse_bin = Path(among_value)

    picat_value = os.environ.get("ONE_SOLUTION_PICAT_BIN")
    if picat_value is None:
        native_picat = native_home / "bin/picat"
        picat_value = str(native_picat) if native_picat.is_file() else "picat"
    picat_bin = executable_path(picat_value, env)
    if "Picat" in methods and picat_bin is None:
        raise SystemExit(f"missing Picat: {picat_value}")
    if picat_bin is None:
        picat_bin = Path(picat_value)

    runlim = shutil.which("runlim", path=env.get("PATH"))
    timeout = shutil.which("timeout", path=env.get("PATH"))
    timing_helper = repo_root / "experiments/src/runner/time_method_process.py"
    if runlim is None:
        raise SystemExit("missing runlim")
    if timeout is None:
        raise SystemExit("missing GNU timeout")
    if not timing_helper.is_file():
        raise SystemExit(f"missing timing helper: {timing_helper}")

    output_root = args.output_root
    if output_root is None:
        output_root = Path(
            os.environ.get(
                "ONE_SOLUTION_OUTPUT_ROOT",
                repo_root / "tmp/amongNurse-one-solution-python",
            )
        )
    output_root = output_root.expanduser()
    if not output_root.is_absolute():
        output_root = repo_root / output_root
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_root / f"{stamp}_{secrets.token_hex(3)}"
    run_dir.mkdir()

    total_runs = len(classes) * len(horizons) * len(methods) * args.repetitions
    print(f"Output dir: {run_dir}")
    print(
        f"Plan: one solution; C={list(classes)}, H={list(horizons)}, "
        f"methods={len(methods)}, repetitions={args.repetitions}, runs={total_runs}"
    )
    print(f"Per-run limits: {args.timeout_s}s; {args.memory_mb} MB RAM")
    print(
        "Primary metric: method_wall_s = perf_counter_ns around "
        "timeout -> fresh method process -> exit; runlim excluded."
    )
    if args.repetitions > 1:
        print("Method order rotates once per repetition; aggregate summary reports median and IQR.")

    failed = 0
    run_number = 0
    interrupted = False
    try:
        for class_id in classes:
            for horizon in horizons:
                for repetition in range(1, args.repetitions + 1):
                    for method in rotated(methods, repetition - 1):
                        run_number += 1
                        base = f"{method}_C{class_id}_H{horizon}"
                        if args.repetitions > 1:
                            base += f"_R{repetition:03d}"
                        prefix = run_dir / base
                        stdout_file = Path(f"{prefix}.stdout.txt")
                        stderr_file = Path(f"{prefix}.stderr.txt")
                        runlim_file = Path(f"{prefix}.runlim.txt")
                        method_time_file = Path(f"{prefix}.method_time.txt")
                        exit_file = Path(f"{prefix}.exit_code.txt")
                        report = Path(f"{prefix}.json")

                        (
                            command,
                            encoding,
                            solver,
                            native_backend,
                            solver_api,
                        ) = method_command(
                            method,
                            class_id,
                            horizon,
                            repo_root,
                            python_bin,
                            among_nurse_bin,
                            picat_bin,
                        )
                        timed_command = [
                            timeout,
                            "--foreground",
                            "--signal=TERM",
                            "--kill-after=5s",
                            f"{args.timeout_s}s",
                            *command,
                        ]
                        runlim_command = [
                            runlim,
                            "-o",
                            str(runlim_file),
                            "-r",
                            str(args.timeout_s + 60),
                            "-s",
                            str(args.memory_mb),
                            sys.executable,
                            "-B",
                            str(timing_helper),
                            "--elapsed-file",
                            str(method_time_file),
                            "--exit-file",
                            str(exit_file),
                            "--",
                            *timed_command,
                        ]

                        print(
                            f"[{run_number}/{total_runs}] C={class_id} H={horizon} "
                            f"R={repetition} | {method_label(method)}: START",
                            flush=True,
                        )
                        with stdout_file.open("w", encoding="utf-8", newline="\n") as stdout, stderr_file.open(
                            "w", encoding="utf-8", newline="\n"
                        ) as stderr:
                            wrapper = subprocess.run(
                                runlim_command,
                                cwd=repo_root,
                                env=env,
                                stdout=stdout,
                                stderr=stderr,
                                check=False,
                            )

                        output = stdout_file.read_text(encoding="utf-8", errors="replace")
                        resources = (
                            runlim_file.read_text(encoding="utf-8", errors="replace")
                            if runlim_file.is_file()
                            else ""
                        )
                        method_wall_s = read_float(method_time_file)
                        exit_code = read_integer(exit_file)
                        if exit_code is None:
                            exit_code = wrapper.returncode if wrapper.returncode >= 0 else 128 - wrapper.returncode
                        solution_value = last_number(output, "solns")
                        solutions = int(solution_value) if solution_value is not None else None
                        samples = runlim_value(resources, "samples")

                        if exit_code == 124:
                            status = "timeout"
                        elif exit_code != 0:
                            status = "error"
                        elif method_wall_s is None:
                            status = "timing_error"
                        elif solutions is None:
                            status = "parse_error"
                        elif solutions != 1:
                            status = "solution_mismatch"
                        else:
                            status = "complete"

                        result = {
                            "status": status,
                            "mode": "one_solution",
                            "method": method,
                            "class_id": class_id,
                            "horizon": horizon,
                            "repetition": repetition,
                            "reported_solutions": solutions,
                            "expected_solutions": 1,
                            "encoding": encoding,
                            "solver": solver,
                            "solver_api": solver_api,
                            "native_backend": native_backend,
                            "method_wall_s": method_wall_s,
                            "timing_boundary": TIMING_BOUNDARY,
                            "timer": TIMER,
                            "reported_time_ms": last_number(output, "time"),
                            "reported_first_solution_ms": last_number(
                                output, "timeToFirstSol"
                            ),
                            "runlim_real_s": runlim_value(resources, "real"),
                            "runlim_samples": samples,
                            "runlim_cpu_s": (
                                runlim_value(resources, "time") if samples else None
                            ),
                            "runlim_space_mb": (
                                runlim_value(resources, "space") if samples else None
                            ),
                            "exit_code": exit_code,
                            "command": command,
                            "timed_command": timed_command,
                            "method_time_file": str(method_time_file),
                            "stdout_file": str(stdout_file),
                            "stderr_file": str(stderr_file),
                            "runlim_file": str(runlim_file),
                        }
                        write_json_atomic(report, result)

                        elapsed = (
                            "-" if method_wall_s is None else f"{method_wall_s:.6f}s"
                        )
                        memory = result["runlim_space_mb"]
                        ram = "-" if memory is None else f"{memory:.1f} MB"
                        label = "OK" if status == "complete" else status.upper()
                        print(
                            f"    {label} | solutions: {solutions} | "
                            f"method wall: {elapsed} | peak RAM: {ram}",
                            flush=True,
                        )
                        if status != "complete":
                            failed += 1
                            print(f"    Report: {report}", flush=True)
    except KeyboardInterrupt:
        interrupted = True
        print("Interrupted; writing summaries for completed runs.", file=sys.stderr)

    completed, recorded = write_summaries(run_dir, args.repetitions)
    print(f"Successful runs: {completed}/{total_runs}. Summary: {run_dir / 'summary.csv'}")
    print(f"Aggregate summary: {run_dir / 'summary_aggregate.csv'}")
    if interrupted:
        return 130
    if failed or recorded != total_runs:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
